#!/usr/bin/env python3
"""Gravitas PostInvocation hook.

After each invocation, persists durable session state to .gravitas/sessions/
for interruption recovery.

Input (stdin): JSON with session context
Output: Writes/updates .gravitas/sessions/<task-id>/state.json
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from impact_graph import build_impact_graph
from session_context import session_dir_for_payload


def criterion_id(criterion: object, index: int) -> str:
    return criterion.get("id") if isinstance(criterion, dict) else f"AC{index}"


def load_state(session_dir: Path) -> dict:
    state_path = session_dir / "state.json"
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {
        "phase": "recon",
        "completed_criteria": [],
        "pending_criteria": [],
        "files_touched": [],
        "known_failures": [],
        "last_successful_action": None,
        "next_action": None
    }


def update_state_from_evidence(state: dict, session_dir: Path) -> dict:
    """Update state by reading the evidence ledger."""
    evidence_path = session_dir / "evidence.jsonl"
    if not evidence_path.exists():
        return state

    files_touched = set(state.get("files_touched", []))
    completed_criteria = set(state.get("completed_criteria", []))
    read_files = set(state.get("read_files", []))

    with open(evidence_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("source") == "write" and entry.get("file"):
                    files_touched.add(entry["file"])
                if entry.get("source") == "read" and entry.get("file"):
                    read_files.add(entry["file"])
                if entry.get("source") == "validator" and entry.get("verdict") == "PASS" and entry.get("exit_code") == 0:
                    completed_criteria.update(entry.get("criterion_ids", []))
            except json.JSONDecodeError:
                pass

    state["files_touched"] = sorted(files_touched)
    state["completed_criteria"] = sorted(completed_criteria)
    state["read_files"] = sorted(read_files)

    contract_path = session_dir / "contract.json"
    contract = json.loads(contract_path.read_text()) if contract_path.exists() else {}
    criteria = contract.get("acceptance_criteria", [])
    criterion_ids = [criterion_id(criterion, index) for index, criterion in enumerate(criteria, 1)]
    state["pending_criteria"] = [identifier for identifier in criterion_ids if identifier not in completed_criteria]

    if state["files_touched"]:
        graph, targets = build_impact_graph(Path.cwd(), state["files_touched"])
        state["impact_graph"] = graph
        state["verification_targets"] = targets

    failures_path = session_dir / "failures.jsonl"
    if failures_path.exists():
        failures = []
        for line in failures_path.read_text().splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("resolved") is not True:
                failures.append(entry)
        state["known_failures"] = failures

    coverage = {identifier: ("PASS" if identifier in completed_criteria else "PENDING") for identifier in criterion_ids}
    (session_dir / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    return state


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}

    session_dir = session_dir_for_payload(payload, create=True)
    state = load_state(session_dir)
    state = update_state_from_evidence(state, session_dir)
    state["last_updated"] = datetime.now(timezone.utc).isoformat()

    state_path = session_dir / "state.json"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)
    print(json.dumps({"injectSteps": [], "terminationBehavior": ""}))


if __name__ == "__main__":
    main()
