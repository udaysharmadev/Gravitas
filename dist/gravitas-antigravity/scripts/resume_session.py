#!/usr/bin/env python3
"""Emit the minimum durable context needed to resume a Gravitas session."""
import argparse
import json
import sys
from pathlib import Path


def find_session_dir() -> Path | None:
    sessions = Path(".gravitas/sessions")
    if not sessions.exists():
        return None
    available = [path for path in sessions.iterdir() if path.is_dir()]
    return max(available, key=lambda path: path.stat().st_mtime) if available else None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def load_jsonl(path: Path) -> list:
    entries = []
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def resume_context(session_dir: Path) -> dict:
    state = load_json(session_dir / "state.json")
    contract = load_json(session_dir / "contract.json")
    failures = load_jsonl(session_dir / "failures.jsonl")
    return {
        "task_id": state.get("task_id", session_dir.name),
        "objective": contract.get("objective"),
        "mode": contract.get("mode"),
        "phase": state.get("phase"),
        "completed_criteria": state.get("completed_criteria", []),
        "pending_criteria": state.get("pending_criteria", []),
        "files_touched": state.get("files_touched", []),
        "read_files": state.get("read_files", []),
        "verification_targets": state.get("verification_targets", []),
        "known_failures": [failure.get("error", failure.get("reason", "unknown")) for failure in failures if failure.get("resolved") is not True],
        "next_action": state.get("next_action"),
    }


def main():
    parser = argparse.ArgumentParser(description="Show compact context for a resumed Gravitas session")
    parser.add_argument("--session-dir")
    args = parser.parse_args()
    session_dir = Path(args.session_dir) if args.session_dir else find_session_dir()
    if not session_dir:
        print("No Gravitas session found.", file=sys.stderr)
        return 1
    print(json.dumps(resume_context(session_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
