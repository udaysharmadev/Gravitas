#!/usr/bin/env python3
"""Run a bug reproducer and record it as criterion-linked evidence.

Reproduction-first protocol: a bug is confirmed by a failing reproducer
run (phase=before), fixed, then the SAME reproducer must pass (phase=after)
before the fix claim counts. Unlike validator_runner, reproducers are
discovered during debugging and need no contract pre-declaration -- but
the criterion must exist.

When reproduction is impossible, record why instead of fabricating one:
``--unreproducible --reason ...`` stores a UNVERIFIABLE record that blocks
the finish gate until the contract is explicitly amended.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from evidence_chain import append_evidence, sha256
from post_tool import redact_text


def load_contract(session_dir: Path) -> dict:
    path = session_dir / "contract.json"
    if not path.exists():
        raise ValueError("session has no contract.json; initialize a structured Gravitas contract first")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("contract.json must contain an object")
    return loaded


def criterion_ids(contract: dict) -> set[str]:
    ids = set()
    for index, item in enumerate(contract.get("acceptance_criteria", []), 1):
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.add(item["id"])
        else:
            ids.add(f"AC{index}")
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Gravitas reproducer")
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--criterion-id", required=True)
    parser.add_argument("--phase", choices=["before", "after"], default="before")
    parser.add_argument("--unreproducible", action="store_true")
    parser.add_argument("--reason", default="")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    try:
        contract = load_contract(session_dir)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.criterion_id not in criterion_ids(contract):
        parser.error(f"criterion {args.criterion_id!r} is not declared by this contract")

    if args.unreproducible:
        if not args.reason:
            parser.error("--unreproducible requires --reason explaining why reproduction is impossible")
        record = {
            "source": "reproducer",
            "criterion_ids": [args.criterion_id],
            "phase": args.phase,
            "verdict": "UNVERIFIABLE",
            "reason": args.reason,
            "evidence": f"reproduction impossible: {args.reason}",
        }
        saved = append_evidence(session_dir, record)
        print(json.dumps({"verdict": "UNVERIFIABLE", "event_hash": saved["event_hash"]}))
        return 0

    if not args.command or args.command[0] != "--":
        parser.error("pass the reproducer command after --")
    command = args.command[1:]
    if not command:
        parser.error("reproducer command cannot be empty")
    cwd = Path(args.cwd).resolve()
    start = time.monotonic()
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    elapsed_ms = round((time.monotonic() - start) * 1000)
    record = {
        "source": "reproducer",
        "criterion_ids": [args.criterion_id],
        "phase": args.phase,
        "command": command,
        "command_sha256": sha256(command),
        "exit_code": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
        "output_snippet": redact_text(result.stdout[-2000:]),
        "duration_ms": elapsed_ms,
        "evidence": f"reproducer ({args.phase}) exited {result.returncode}",
        "verdict": "PASS" if result.returncode == 0 else "FAIL",
    }
    saved = append_evidence(session_dir, record)
    print(json.dumps({"verdict": saved["verdict"], "exit_code": result.returncode,
                      "event_hash": saved["event_hash"]}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
