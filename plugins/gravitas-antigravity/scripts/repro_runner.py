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
import tempfile
import time
from pathlib import Path

from evidence_chain import append_evidence, sha256
from gravitas_action import confine_cwd
from post_tool import redact_text

DEFAULT_TIMEOUT = 300
OUTPUT_CAP = 1_000_000


def run_bounded(command: list[str], cwd: Path, timeout: int) -> tuple[int, bytes, bytes, bool, int]:
    start = time.monotonic()
    with tempfile.TemporaryFile() as out_f, tempfile.TemporaryFile() as err_f:
        try:
            proc = subprocess.run(command, cwd=cwd, stdout=out_f, stderr=err_f,
                                  check=False, timeout=timeout)
            rc, timed_out = proc.returncode, False
        except subprocess.TimeoutExpired:
            rc, timed_out = 124, True
        elapsed_ms = round((time.monotonic() - start) * 1000)
        out_f.seek(0)
        err_f.seek(0)
        return rc, out_f.read(OUTPUT_CAP + 1)[:OUTPUT_CAP], err_f.read(OUTPUT_CAP + 1)[:OUTPUT_CAP], timed_out, elapsed_ms


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
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
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
        try:
            saved = append_evidence(session_dir, record)
        except (OSError, ValueError) as error:
            print(json.dumps({"verdict": "UNVERIFIABLE",
                              "evidence_error": f"evidence append failed: {error}"}))
            return 1
        print(json.dumps({"verdict": "UNVERIFIABLE", "event_hash": saved["event_hash"]}))
        return 0

    if not args.command or args.command[0] != "--":
        parser.error("pass the reproducer command after --")
    command = args.command[1:]
    if not command:
        parser.error("reproducer command cannot be empty")
    try:
        cwd = confine_cwd(args.cwd)
    except ValueError as error:
        parser.error(str(error))
    start = time.monotonic()
    rc, out_b, err_b, timed_out, elapsed_ms = run_bounded(command, cwd, args.timeout)
    stdout_text = out_b.decode("utf-8", errors="replace")
    record = {
        "source": "reproducer",
        "criterion_ids": [args.criterion_id],
        "phase": args.phase,
        "command": command,
        "command_sha256": sha256(command),
        "exit_code": rc,
        "stdout_sha256": hashlib.sha256(out_b).hexdigest(),
        "stderr_sha256": hashlib.sha256(err_b).hexdigest(),
        "output_snippet": redact_text(stdout_text[-2000:]),
        "duration_ms": elapsed_ms,
        "timed_out": timed_out,
        "evidence": f"reproducer ({args.phase}) {'timed out' if timed_out else f'exited {rc}'}",
        "verdict": "FAIL" if (timed_out or rc != 0) else "PASS",
    }
    try:
        saved = append_evidence(session_dir, record)
    except (OSError, ValueError) as error:
        print(json.dumps({"verdict": record["verdict"], "exit_code": rc,
                          "timed_out": timed_out,
                          "evidence_error": f"evidence append failed: {error}"}))
        return 1
    print(json.dumps({"verdict": saved["verdict"], "exit_code": rc,
                      "timed_out": timed_out, "event_hash": saved["event_hash"]}))
    return rc if not timed_out else 124


if __name__ == "__main__":
    raise SystemExit(main())
