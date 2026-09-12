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
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from session_context import session_dir_for_payload


def load_contract(session_dir: Path) -> dict:
    contract_path = session_dir / "contract.json"
    if contract_path.exists():
        with open(contract_path) as f:
            return json.load(f)
    return {}


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


def owned_validator_pass(entry: dict) -> bool:
    """Only Gravitas-owned executions are completion-grade evidence."""
    return (
        entry.get("source") == "validator"
        and entry.get("verdict") == "PASS"
        and entry.get("exit_code") == 0
        and isinstance(entry.get("validator_id"), str)
        and isinstance(entry.get("event_hash"), str)
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"decision": "allow"}))
        return

    session_dir = session_dir_for_payload(payload)

    # If no session, allow stop (no contract to enforce)
    if not session_dir:
        print(json.dumps({"decision": "allow"}))
        return

    contract = load_contract(session_dir)
    evidence = load_evidence(session_dir)
    state = load_state(session_dir)
    failures = load_failures(session_dir)

    if payload.get("fullyIdle") is False:
        reason = "Completion gate: Antigravity reports active background work."
        record_stop_gate_cycle(session_dir, "continue", reason)
        print(json.dumps({"decision": "continue", "reason": reason}))
        return

    # Circuit breaker: stop automatic retries, but never fail open.
    cycle_count = count_stop_gate_cycles(session_dir)
    if cycle_count >= 3:
        record_stop_gate_cycle(session_dir, "continue", "circuit breaker: 3+ cycles")
        print(json.dumps({
            "decision": "continue",
            "reason": "Completion gate circuit breaker: 3+ verification cycles. "
                      "Automatic retries are exhausted; resolve or amend the contract manually."
        }))
        return

    # Check acceptance criteria coverage
    acceptance_criteria = contract.get("acceptance_criteria", [])
    uncovered = []

    for index, criterion in enumerate(acceptance_criteria, 1):
        identifier = criterion_id(criterion, index)
        has_evidence = any(
            identifier in entry.get("criterion_ids", []) and owned_validator_pass(entry)
            for entry in evidence
        )
        if not has_evidence:
            uncovered.append(criterion_label(criterion, index))

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

    # Legacy command fragments are retained only as a migration diagnostic. New
    # contracts name validators, which are matched by ID and captured exit code.
    required_validators = contract.get("required_validators", [])
    required_validator_ids = [validator.get("id") for validator in contract.get("validators", [])]
    missing_validators = [
        validator for validator in required_validators
        if not any(
            validator in " ".join(entry.get("command", [])) and owned_validator_pass(entry)
            for entry in evidence
        )
    ]
    missing_validators.extend(
        validator_id for validator_id in required_validator_ids
        if not any(entry.get("validator_id") == validator_id and owned_validator_pass(entry) for entry in evidence)
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
    known_failures = state.get("known_failures", []) or [f for f in failures if f.get("resolved") is not True]
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
