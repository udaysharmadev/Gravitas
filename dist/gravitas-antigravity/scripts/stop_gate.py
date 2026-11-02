#!/usr/bin/env python3
"""Gravitas Stop hook -- Completion gate.

Before allowing the agent to stop, verifies:
1. All acceptance criteria have evidence in the ledger
2. Required validators were observed to run
3. No known failures are unresolved
4. Circuit breaker: prevents infinite loops

Input (stdin): JSON with agent_response, session_state
Output (stdout): JSON with decision: allow|continue and optional reason
"""
from __future__ import annotations
import json
import shlex
import sys
from pathlib import Path
from datetime import datetime, timezone
from session_context import session_dir_for_payload
from evidence_chain import verify_with_anchor
from evidence_chain import resolution_matches, resolution_records
from gravitas_evidence import (
    criterion_states,
    declared_validator_pass,
    evidence_deficit,
    is_fresh,
    opencode_completion_writes,
    owned_validator_pass,
)

#: Stop-gate attempt budget: after this many continue cycles the gate must
#: terminate safely instead of looping forever. Termination is explicit
#: unverified (decision allow + unverified:true), never a false PASS.


def legacy_requirement_met(requirement: object, entry: dict) -> bool:
    """Exact match of a legacy ``required_validators`` item against one evidence entry.

    A requirement is met only by the entry's validator id or by the whole recorded
    command line. A substring test would let ``"test"`` be satisfied by
    ``echo latest``.
    """
    if not isinstance(requirement, str) or not requirement:
        return False
    if entry.get("validator_id") == requirement:
        return True
    command = entry.get("command")
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        return False
    return requirement == shlex.join(command)


def load_contract(session_dir: Path) -> dict | None:
    contract_path = session_dir / "contract.json"
    if not contract_path.exists():
        return None
    try:
        with open(contract_path) as f:
            contract = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return contract if isinstance(contract, dict) else None


def load_evidence(session_dir: Path) -> list:
    evidence_path = session_dir / "evidence.jsonl"
    if not evidence_path.exists():
        return []
    evidence = []
    with open(evidence_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    evidence.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return evidence


def load_state(session_dir: Path) -> dict:
    state_path = session_dir / "state.json"
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {}


def load_failures(session_dir: Path) -> list:
    failures_path = session_dir / "failures.jsonl"
    if not failures_path.exists():
        return []
    failures = []
    with open(failures_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    failures.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return failures


def active_failures(failures: list, resolutions: dict) -> list:
    """Apply resolution markers in order so a later failure re-arms its ban."""
    latest_by_fingerprint = {}
    unkeyed = []
    for entry in failures:
        if not isinstance(entry, dict):
            continue
        fingerprint = entry.get("fingerprint")
        if not fingerprint:
            if not resolution_matches(entry, resolutions.get(entry.get("resolution_id"))):
                unkeyed.append(entry)
            continue
        latest_by_fingerprint[fingerprint] = entry
    return unkeyed + [
        entry for entry in latest_by_fingerprint.values()
        if not resolution_matches(entry, resolutions.get(entry.get("resolution_id")))
    ]


def count_stop_gate_cycles(session_dir: Path) -> int:
    """Count how many times the stop gate has fired in this session."""
    gate_log = session_dir / "stop_gate.log"
    if not gate_log.exists():
        return 0
    with open(gate_log) as f:
        return sum(1 for line in f if line.strip())


def record_stop_gate_cycle(session_dir: Path, decision: str, reason: str):
    gate_log = session_dir / "stop_gate.log"
    with open(gate_log, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "reason": reason
        }) + "\n")


def criterion_id(criterion: object, index: int) -> str:
    return criterion.get("id") if isinstance(criterion, dict) else f"AC{index}"


def criterion_label(criterion: object, index: int) -> str:
    return criterion.get("statement", criterion.get("id", "")) if isinstance(criterion, dict) else str(criterion)


def resolution_deficits(failures: list, evidence: list, contract: dict) -> list[str]:
    """Require each resolved failure's declared re-read and validation evidence."""
    from gravitas_evidence import parse_time
    import os

    validators = {
        validator.get("id"): validator
        for validator in contract.get("validators", [])
        if isinstance(validator, dict) and isinstance(validator.get("id"), str)
    }
    deficits = []
    ledger_resolutions = resolution_records(evidence)
    failure_resolution_ids = {
        marker.get("resolution_id")
        for marker in failures
        if isinstance(marker, dict)
        and marker.get("resolved") is True
        and isinstance(marker.get("resolution_id"), str)
    }
    for identifier in ledger_resolutions.keys() - failure_resolution_ids:
        deficits.append(f"{identifier}: anchored resolution is missing its failure-log marker")

    latest_by_fingerprint = {}
    unkeyed = []
    for marker in failures:
        if not isinstance(marker, dict):
            continue
        fingerprint = marker.get("fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            latest_by_fingerprint[fingerprint] = marker
        else:
            unkeyed.append(marker)

    for marker in [*latest_by_fingerprint.values(), *unkeyed]:
        if marker.get("resolved") is not True:
            continue
        resolved_at = parse_time(marker.get("timestamp"))
        resolution_id = marker.get("resolution_id", marker.get("fingerprint", "unknown"))
        anchored = ledger_resolutions.get(resolution_id)
        if not resolution_matches(marker, anchored):
            deficits.append(f"{resolution_id}: resolution metadata is not anchored")
            continue
        if resolved_at is None:
            deficits.append(f"{resolution_id}: resolution timestamp is invalid")
            continue

        required_reads = marker.get("required_reads")
        if not isinstance(required_reads, list) or not required_reads:
            required_reads = ["*"]
        later_reads = []
        for entry in evidence:
            if not isinstance(entry, dict):
                continue
            if entry.get("source") != "read":
                continue
            if resolution_id not in entry.get("resolution_ids", []):
                continue
            read_at = parse_time(entry.get("timestamp"))
            if read_at is None or read_at <= resolved_at:
                continue
            recorded_file = entry.get("file")
            if not isinstance(recorded_file, str) or not recorded_file:
                continue
            later_reads.append((recorded_file, entry))

        missing_reads = []
        for target in required_reads:
            if target == "*" and later_reads:
                continue
            if target != "*":
                target_path = os.path.normcase(os.path.abspath(target))
                if any(os.path.normcase(os.path.abspath(recorded)) == target_path
                       for recorded, _ in later_reads):
                    continue
            missing_reads.append(target)

        required_criteria = marker.get("criterion_ids", [])
        missing_criteria = []
        if not isinstance(required_criteria, list):
            missing_criteria = ["invalid criterion list"]
        else:
            for criterion_id in required_criteria:
                candidates = [
                    entry for entry in evidence
                    if isinstance(entry, dict)
                    and entry.get("source") == "validator"
                    and resolution_id in entry.get("resolution_ids", [])
                    and criterion_id in (entry.get("criterion_ids", []) or [])
                    and entry.get("verdict") == "PASS"
                    and entry.get("exit_code") == 0
                    and isinstance(entry.get("event_hash"), str)
                    and isinstance(entry.get("validator_id"), str)
                    and parse_time(entry.get("timestamp")) is not None
                ]
                candidates = [
                    entry for entry in candidates
                    if parse_time(entry.get("timestamp")) > resolved_at
                    and is_fresh(entry, evidence)
                    and (
                        not validators
                        or (
                            entry.get("validator_id") in validators
                            and declared_validator_pass(
                                entry, validators[entry["validator_id"]]
                            )
                        )
                    )
                ]
                if not candidates:
                    missing_criteria.append(criterion_id)

        if missing_reads or missing_criteria:
            details = []
            if missing_reads:
                details.append("re-read " + ", ".join(missing_reads))
            if missing_criteria:
                details.append("fresh validator PASS for " + ", ".join(missing_criteria))
            deficits.append(f"{resolution_id}: " + " and ".join(details))
    return deficits


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Unparseable payload: cannot verify anything, so do not allow stop
        # as verified completion.
        print(json.dumps({"decision": "continue",
                          "reason": "Completion gate: hook payload unparseable; cannot verify completion"}))
        return

    session_dir = session_dir_for_payload(payload)

    # If no session, allow stop (no contract to enforce)
    if not session_dir:
        print(json.dumps({"decision": "allow"}))
        return

    contract = load_contract(session_dir)
    if contract is None:
        reason = "Completion gate: contract is missing or invalid; cannot verify completion"
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    acceptance_criteria = contract.get("acceptance_criteria")
    if not isinstance(acceptance_criteria, list) or not acceptance_criteria:
        reason = "Completion gate: contract declares no acceptance criteria; define what done means before stopping"
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    evidence = load_evidence(session_dir)
    if payload.get("host") == "opencode":
        session_id = payload.get("sessionID", payload.get("session_id", ""))
        if isinstance(session_id, str) and session_id:
            evidence.extend(opencode_completion_writes(
                Path.cwd() / ".gravitas" / "opencode-completions.jsonl", session_id
            ))
    state = load_state(session_dir)
    failures = load_failures(session_dir)

    if payload.get("fullyIdle") is False:
        reason = "Completion gate: Antigravity reports active background work."
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    # Chain integrity comes first: a rewritten/tampered ledger must not gate
    # allow no matter how convincing the verdicts look.
    valid, chain_reason = verify_with_anchor(session_dir)
    if not valid:
        reason = f"Completion gate: evidence chain invalid ({chain_reason}); refusing completion"
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    # Circuit breaker: after 3+ cycles terminate safely as EXPLICITLY
    # UNVERIFIED (allows the host to stop without ever reporting false PASS).
    cycle_count = count_stop_gate_cycles(session_dir)
    if cycle_count >= 3:
        states_cb = criterion_states(contract, evidence)
        deficit_cb = evidence_deficit(contract, states_cb)
        reason = ("Completion gate circuit breaker: 3+ verification cycles. "
                  "Terminating as UNVERIFIED, not as completion: "
                  + "; ".join(f"{d['criterion']} ({d['status']})" for d in deficit_cb[:5]))
        record_stop_gate_cycle(session_dir, "allow-unverified", reason)
        print(json.dumps({
            "decision": "allow",
            "unverified": True,
            "reason": reason,
            "deficit": deficit_cb,
        }))
        return

    # Acceptance criteria gate on fresh owned evidence only. Stale PASS
    # (written before the final mutation), SUPPORTED, FAIL, BLOCKED, and
    # UNVERIFIABLE all block with the deficit action attached.
    states = criterion_states(contract, evidence)
    deficit = {item["criterion"]: item for item in evidence_deficit(contract, states)}
    uncovered = []
    for index, criterion in enumerate(acceptance_criteria, 1):
        identifier = criterion_id(criterion, index)
        if states.get(identifier, {}).get("status") != "PASS":
            need = deficit.get(identifier, {}).get("needed", "record evidence")
            uncovered.append(f"{criterion_label(criterion, index)} [{need}]")

    if uncovered:
        reason = (
            f"Completion gate: {len(uncovered)} acceptance criteria have no verification evidence: "
            + "; ".join(f'"{c}"' for c in uncovered[:3])
            + (" and more" if len(uncovered) > 3 else "")
            + ". Run the required validators and record evidence before stopping."
        )
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    pending_resolutions = resolution_deficits(failures, evidence, contract)
    if pending_resolutions:
        reason = ("Completion gate: resolved failures still need post-resolution evidence: "
                  + "; ".join(pending_resolutions[:3])
                  + (" and more" if len(pending_resolutions) > 3 else ""))
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    # Legacy command fragments are retained only as a migration diagnostic. New
    # contracts name validators, which are matched by ID and captured exit code.
    required_validators = contract.get("required_validators", [])
    declared_validators = {
        validator.get("id"): validator
        for validator in contract.get("validators", [])
        if isinstance(validator, dict) and isinstance(validator.get("id"), str)
    }
    required_validator_ids = list(declared_validators)
    missing_validators = [
        validator for validator in required_validators
        if not any(
            legacy_requirement_met(validator, entry) and owned_validator_pass(entry) and is_fresh(entry, evidence)
            for entry in evidence
        )
    ]
    missing_validators.extend(
        validator_id for validator_id in required_validator_ids
        if not any(
            entry.get("validator_id") == validator_id
            and declared_validator_pass(entry, declared_validators[validator_id])
            and is_fresh(entry, evidence)
            for entry in evidence
        )
    )
    if missing_validators:
        reason = "Completion gate: required validators missing or failing: " + ", ".join(missing_validators)
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    running_tasks = [task for task in state.get("background_tasks", []) if task.get("status") == "running"]
    if running_tasks:
        reason = f"Completion gate: {len(running_tasks)} background task(s) still running."
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    # Check for unresolved failures
    known_failures = active_failures(failures, resolution_records(evidence))
    if known_failures:
        reason = (
            f"Completion gate: {len(known_failures)} known failures are unresolved: "
            + "; ".join(str(f) for f in known_failures[:2])
            + ". Resolve these before stopping."
        )
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    # All checks passed
    record_stop_gate_cycle(session_dir, "allow", "all criteria covered")
    print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
