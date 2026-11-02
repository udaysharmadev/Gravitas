#!/usr/bin/env python3
"""Requirement-evidence graph: per-criterion states from ledger evidence.

States: PENDING (no evidence), SUPPORTED (non-owned evidence only -- never
gates completion), PASS (fresh Gravitas-owned validator PASS), FAIL
(latest owned verdict is FAIL), BLOCKED (contract-declared with reason),
UNVERIFIABLE (reproduction impossible, recorded with reason).

Freshness: a PASS is fresh only if its timestamp is strictly newer than
the latest file-write entry in the ledger. Evidence created before the
final mutation cannot satisfy the finish gate.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATES = ("PENDING", "SUPPORTED", "PASS", "FAIL", "BLOCKED", "UNVERIFIABLE")

OWNED_SOURCES = ("validator",)

UNKNOWN_WRITE_TIME = datetime.max.replace(tzinfo=timezone.utc)


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def owned_validator_pass(entry: dict) -> bool:
    """Only Gravitas-owned executions are completion-grade evidence."""
    return (
        entry.get("source") == "validator"
        and entry.get("verdict") == "PASS"
        and entry.get("exit_code") == 0
        and isinstance(entry.get("validator_id"), str)
        and isinstance(entry.get("event_hash"), str)
    )


def declared_validator_pass(entry: dict, validator: dict) -> bool:
    """Require completion evidence to use the contract-declared argv."""
    return (
        owned_validator_pass(entry)
        and entry.get("command") == validator.get("command")
    )


def last_write_time(evidence: list[dict]) -> datetime | None:
    latest = None
    for entry in evidence:
        if isinstance(entry, dict) and entry.get("source") == "write":
            moment = parse_time(entry.get("timestamp"))
            if moment is None:
                return UNKNOWN_WRITE_TIME
            if latest is None or moment > latest:
                latest = moment
    return latest


def opencode_completion_writes(path, session_id: str) -> list[dict]:
    """Convert successful, session-matched OpenCode mutations into dirty evidence."""
    if not session_id:
        return []
    path = Path(path)
    if not path.exists():
        return []
    writes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except (ValueError, TypeError):
            continue
        if (not isinstance(entry, dict)
                or entry.get("session_id") != session_id
                or entry.get("success") is not True):
            continue
        tool = entry.get("tool")
        mutating = tool in ("edit", "write", "patch")
        if tool == "bash":
            args = entry.get("args")
            command = args.get("command") if isinstance(args, dict) else None
            if isinstance(command, str) and command:
                from gravitas_action import classify_shell
                mutating = classify_shell(command).get("mutation") in (
                    "mutation", "destructive", "write"
                )
            else:
                mutating = True
        if not mutating:
            continue
        writes.append({
            "source": "write",
            "file": None,
            "timestamp": entry.get("timestamp"),
            "opencode_session_id": session_id,
            "completion_tool": tool,
        })
    return writes


def is_fresh(entry: dict, evidence: list[dict]) -> bool:
    moment = parse_time(entry.get("timestamp"))
    if moment is None:
        return False
    cutoff = last_write_time(evidence)
    if cutoff is UNKNOWN_WRITE_TIME:
        return False
    return cutoff is None or moment > cutoff


def criterion_states(contract: dict, evidence: list[dict]) -> dict:
    """Map criterion id -> {statement, status, evidence, fresh}."""
    states = {}
    for index, criterion in enumerate(contract.get("acceptance_criteria", []), 1):
        if isinstance(criterion, dict):
            identifier = criterion.get("id", f"AC{index}")
            statement = criterion.get("statement", identifier)
            declared = criterion.get("status")
        else:
            identifier = f"AC{index}"
            statement = str(criterion)
            declared = None
        if declared in ("BLOCKED", "UNVERIFIABLE") and isinstance(criterion, dict) and criterion.get("reason"):
            states[identifier] = {"statement": statement, "status": declared,
                                  "evidence": [], "fresh": False,
                                  "reason": criterion["reason"]}
            continue
        linked = [e for e in evidence if identifier in (e.get("criterion_ids", []) or [])]
        owned = [e for e in linked if e.get("source") in OWNED_SOURCES]
        fresh_owned = sorted(
            (e for e in owned if is_fresh(e, evidence)),
            key=lambda e: parse_time(e.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc))
        # Latest fresh owned verdict governs: a FAIL after a PASS means the
        # criterion is currently failing, not satisfied.
        latest = fresh_owned[-1] if fresh_owned else None
        fresh_pass = latest is not None and owned_validator_pass(latest)
        fresh_fail = latest is not None and latest.get("verdict") == "FAIL"
        stale_owned = [e for e in owned if not is_fresh(e, evidence)]
        reproducer = [e for e in linked if e.get("source") == "reproducer"]
        unverifiable = [e for e in reproducer if e.get("verdict") == "UNVERIFIABLE"]
        other = [e for e in linked if e.get("source") not in OWNED_SOURCES + ("reproducer",)
                 and e.get("verdict") in ("PASS", "CONDITIONAL_PASS")]
        if fresh_pass:
            status = "PASS"
        elif unverifiable:
            status = "UNVERIFIABLE"
        elif fresh_fail:
            status = "FAIL"
        elif other or reproducer:
            status = "SUPPORTED"
        else:
            status = "PENDING"
        states[identifier] = {
            "statement": statement,
            "status": status,
            "evidence": [e.get("event_hash", e.get("evidence", "")) for e in linked],
            "fresh": bool(fresh_pass),
            "stale_owned": len(stale_owned),
        }
    return states


def evidence_deficit(contract: dict, states: dict) -> list[dict]:
    """Ordered next-actions from evidence gaps (PENDING first)."""
    order = {"PENDING": 0, "FAIL": 1, "UNVERIFIABLE": 2, "SUPPORTED": 3}
    deficit = []
    for identifier, info in states.items():
        status = info["status"]
        if status == "PASS":
            continue
        if status == "PENDING":
            need = ("run a contract-declared validator covering this criterion "
                    "through gravitas validator and bind it with --criterion-id")
        elif status == "FAIL":
            need = "diagnose the latest FAIL evidence, change the approach, then re-run"
        elif status == "UNVERIFIABLE":
            need = "reproduction impossible as recorded; amend the contract explicitly to proceed"
        else:
            need = ("non-owned evidence only; run a Gravitas-owned validator "
                    "after the final mutation for completion-grade proof")
        deficit.append({"criterion": identifier, "status": status,
                        "statement": info["statement"], "needed": need,
                        "stale_owned": info.get("stale_owned", 0)})
    return sorted(deficit, key=lambda d: (order.get(d["status"], 9), d["criterion"]))
