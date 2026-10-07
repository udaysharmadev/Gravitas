#!/usr/bin/env python3
"""Context pressure management and durable session summaries.

- :func:`elide_output`: deterministically shrink oversized tool output.
  Keeps the head and tail, preserves error/failure lines verbatim, and
  reports exactly what was dropped (line counts + digest). Critical
  identifiers are never paraphrased -- they are either kept or the drop
  is declared.
- :func:`summarize_session`: rebuild the durable compact state from
  contract.json, state.json, coverage.json, evidence.jsonl, and
  failures.jsonl. Every structured field from the recovery contract is
  present; free-text values are quoted verbatim (truncated, never
  rewritten).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

KEEP_PATTERN = re.compile(
    r"(?i)\b(error|fail|exception|traceback|assert|panic|fatal|denied|violation)\b|"
    r"^\s*(PASS|FAIL|ok|not ok|VERDICT)")


def elide_output(text: str, *, budget_lines: int = 60,
                 head_lines: int = 20) -> dict:
    """Shrink text to a line budget deterministically.

    Returns {"text": ..., "elided": bool, "dropped_lines": int,
    "kept_lines": int, "sha256": ...}. When nothing is dropped, text is
    returned unchanged with elided=False.
    """
    lines = text.splitlines()
    if len(lines) <= budget_lines:
        return {"text": text, "elided": False, "dropped_lines": 0,
                "kept_lines": len(lines),
                "sha256": hashlib.sha256(text.encode()).hexdigest()}
    tail_lines = max(budget_lines - head_lines, 10)
    head, tail = lines[:head_lines], lines[-tail_lines:]
    middle = lines[head_lines: len(lines) - tail_lines]
    kept_errors = [line for line in middle if KEEP_PATTERN.search(line)]
    dropped = len(middle) - len(kept_errors)
    banner = (f"[... elided {dropped} lines "
              f"(sha256 of full output: {hashlib.sha256(text.encode()).hexdigest()[:16]}) ...]")
    kept = head + ([banner] if dropped else []) + kept_errors + tail
    shrunk = "\n".join(kept)
    return {"text": shrunk, "elided": True, "dropped_lines": dropped,
            "kept_lines": len(kept),
            "sha256": hashlib.sha256(text.encode()).hexdigest()}


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> list:
    entries = []
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _truncate(value: object, limit: int = 500) -> object:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f" [... truncated {len(value) - limit} chars]"
    return value


def summarize_session(session_dir: Path) -> dict:
    """Build the durable compact state for handoff or resume.

    Fields: objective, mode, acceptance criteria + statuses, allowed
    scope, phase, files inspected/modified, findings, decisions, failed
    approaches + root causes, validators executed, latest evidence,
    unresolved risks, next action. Verbatim values only.
    """
    session_dir = Path(session_dir)
    contract = _read_json(session_dir / "contract.json", {})
    state = _read_json(session_dir / "state.json", {})
    coverage = _read_json(session_dir / "coverage.json", {})
    evidence = _read_jsonl(session_dir / "evidence.jsonl")
    failures = _read_jsonl(session_dir / "failures.jsonl")

    criteria = contract.get("acceptance_criteria", [])
    criterion_status = {}
    for index, criterion in enumerate(criteria, 1):
        identifier = criterion.get("id") if isinstance(criterion, dict) else f"AC{index}"
        statement = criterion.get("statement") if isinstance(criterion, dict) else str(criterion)
        status = coverage.get(identifier, "PENDING")
        if status not in ("PENDING", "SUPPORTED", "PASS", "FAIL", "BLOCKED", "UNVERIFIABLE"):
            status = "PENDING"
        criterion_status[identifier] = {"statement": statement, "status": status}

    validators = []
    latest_evidence = None
    for entry in evidence:
        if entry.get("source") == "validator" and isinstance(entry.get("validator_id"), str):
            validators.append({
                "validator_id": entry["validator_id"],
                "criterion_ids": entry.get("criterion_ids", []),
                "verdict": entry.get("verdict"),
                "exit_code": entry.get("exit_code"),
                "event_hash": entry.get("event_hash"),
            })
            latest_evidence = entry.get("event_hash")
    seen_validators = []
    for item in validators:
        if item not in seen_validators:
            seen_validators.append(item)

    failed_approaches = []
    for entry in failures:
        if entry.get("resolved") is True:
            continue
        failed_approaches.append({
            "tool": entry.get("tool"),
            "fingerprint": entry.get("fingerprint"),
            "cause": _truncate(entry.get("error", entry.get("reason", "unknown"))),
        })

    decisions = state.get("decisions", [])
    risks = state.get("unresolved_risks", state.get("known_risks", []))
    return {
        "session": session_dir.name,
        "objective": contract.get("objective"),
        "mode": contract.get("mode"),
        "acceptance_criteria": criterion_status,
        "allowed_scope": contract.get("allowed_write_scope", []),
        "phase": state.get("phase"),
        "files_inspected": sorted(set(state.get("read_files", []))),
        "files_modified": sorted(set(state.get("files_touched", []))),
        "findings": state.get("findings", []),
        "decisions": decisions,
        "failed_approaches": failed_approaches,
        "validators_executed": seen_validators,
        "latest_evidence": latest_evidence,
        "unresolved_risks": risks if isinstance(risks, list) else [],
        "next_action": state.get("next_action"),
    }
