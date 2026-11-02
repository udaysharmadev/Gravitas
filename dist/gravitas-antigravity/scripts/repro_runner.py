#!/usr/bin/env python3
"""Run a bug reproducer and record it as criterion-linked evidence.

Reproduction-first protocol: a bug is confirmed by a failing reproducer
run (phase=before), fixed, then the SAME reproducer must pass (phase=after)
before the fix claim counts. Contracts may declare reproducible commands;
legacy contracts bind an after run to the most recent before command hash.

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

from evidence_chain import append_evidence, sha256, verify_chain
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


def configured_reproducers(contract: dict, criteria: set[str]) -> dict[str, dict]:
    definitions = contract.get("reproducers", [])
    if not isinstance(definitions, list):
        raise TypeError("contract reproducers must be a list")
    configured = {}
    for item in definitions:
        if not isinstance(item, dict):
            raise TypeError("each reproducer must be an object")
        reproducer_id = item.get("id")
        command = item.get("command")
        linked_criteria = item.get("criterion_ids")
        if not isinstance(reproducer_id, str) or not reproducer_id:
            raise ValueError("each reproducer requires a non-empty id")
        if reproducer_id in configured:
            raise ValueError(f"duplicate reproducer id {reproducer_id!r}")
        if (not isinstance(command, list) or not command
                or any(not isinstance(part, str) for part in command)
                or not command[0]):
            raise ValueError(f"reproducer {reproducer_id!r} requires a non-empty string command")
        if (not isinstance(linked_criteria, list) or not linked_criteria
                or any(not isinstance(value, str) or value not in criteria
                       for value in linked_criteria)):
            raise ValueError(f"reproducer {reproducer_id!r} requires declared criterion_ids")
        configured[reproducer_id] = {
            "command": command,
            "criterion_ids": set(linked_criteria),
        }
    return configured


def latest_before(session_dir: Path, criterion_id: str, reproducer_id: str | None) -> dict | None:
    path = session_dir / "evidence.jsonl"
    if not path.exists():
        return None
    valid, reason = verify_chain(path)
    if not valid:
        raise ValueError(f"evidence ledger is invalid: {reason}")
    match = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("evidence ledger contains invalid JSON") from error
        if not isinstance(entry, dict):
            raise ValueError("evidence ledger contains a non-object record")
        if entry.get("source") != "reproducer" or entry.get("phase") != "before":
            continue
        linked_criteria = entry.get("criterion_ids")
        if not isinstance(linked_criteria, list) or any(
            not isinstance(identifier, str) for identifier in linked_criteria
        ):
            raise ValueError("evidence ledger contains invalid reproducer criterion links")
        if criterion_id in linked_criteria and entry.get("reproducer_id") == reproducer_id:
            match = entry
    return match


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Gravitas reproducer")
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--criterion-id", required=True)
    parser.add_argument("--reproducer-id")
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
    criteria = criterion_ids(contract)
    if args.criterion_id not in criteria:
        parser.error(f"criterion {args.criterion_id!r} is not declared by this contract")
    try:
        reproducers = configured_reproducers(contract, criteria)
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    if reproducers and not args.reproducer_id:
        parser.error("--reproducer-id is required by this contract")
    if args.reproducer_id and args.reproducer_id not in reproducers:
        parser.error(f"reproducer {args.reproducer_id!r} is not declared by this contract")
    definition = reproducers.get(args.reproducer_id) if args.reproducer_id else None
    if definition and args.criterion_id not in definition["criterion_ids"]:
        parser.error(f"reproducer {args.reproducer_id!r} is not linked to criterion {args.criterion_id!r}")

    if args.unreproducible:
        if not args.reason:
            parser.error("--unreproducible requires --reason explaining why reproduction is impossible")
        record = {
            "source": "reproducer",
            "criterion_ids": [args.criterion_id],
            **({"reproducer_id": args.reproducer_id} if args.reproducer_id else {}),
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
    if definition and command != definition["command"]:
        parser.error(f"command differs from the declared reproducer {args.reproducer_id!r}")
    command_hash = sha256(command)
    try:
        cwd = confine_cwd(args.cwd)
    except ValueError as error:
        parser.error(str(error))
    if args.phase == "after":
        try:
            before = latest_before(session_dir, args.criterion_id, args.reproducer_id)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        if not before:
            parser.error("an after reproducer requires a matching before run")
        if not isinstance(before.get("event_hash"), str):
            parser.error("the matching before reproducer is not hash-linked evidence")
        if before.get("verdict") != "FAIL":
            parser.error("the matching before reproducer must have a FAIL verdict")
        before_command = before.get("command")
        if (
            not isinstance(before_command, list)
            or not before_command
            or any(not isinstance(part, str) for part in before_command)
            or not before_command[0]
            or sha256(before_command) != before.get("command_sha256")
        ):
            parser.error("the matching before reproducer has an invalid command identity")
        exit_code = before.get("exit_code")
        timed_out = before.get("timed_out")
        if (
            not isinstance(exit_code, int)
            or isinstance(exit_code, bool)
            or not isinstance(timed_out, bool)
        ):
            parser.error("the matching before reproducer has an invalid execution result")
        if (timed_out and exit_code != 124) or (not timed_out and exit_code == 0):
            parser.error("the matching before reproducer has an invalid FAIL result")
        if before.get("command_sha256") != command_hash:
            parser.error("after command does not match the most recent before command")
        if before_command != command:
            parser.error("after command does not match the most recent before command")
        if before.get("working_directory") != str(cwd):
            parser.error("after working directory does not match the most recent before run")
    start = time.monotonic()
    rc, out_b, err_b, timed_out, elapsed_ms = run_bounded(command, cwd, args.timeout)
    stdout_text = out_b.decode("utf-8", errors="replace")
    record = {
        "source": "reproducer",
        "criterion_ids": [args.criterion_id],
        **({"reproducer_id": args.reproducer_id} if args.reproducer_id else {}),
        "phase": args.phase,
        "command": command,
        "command_sha256": command_hash,
        "working_directory": str(cwd),
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
