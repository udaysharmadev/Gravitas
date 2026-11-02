#!/usr/bin/env python3
"""Run a validator and capture the only completion-grade runtime evidence.

Hook payloads are telemetry, not proof: Antigravity's documented PostToolUse
payload does not promise stdout or an exit code. This runner owns execution and
records the command's exit status, bounded digests, and a hash-linked event.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path

from evidence_chain import append_evidence, resolution_links, sha256
from gravitas_action import confine_cwd

#: Default wall-clock bound per validator execution (seconds).
DEFAULT_TIMEOUT = 300
#: Bytes of stdout/stderr retained for hashing/diagnosis (rest discarded).
OUTPUT_CAP = 1_000_000


def run_bounded(command: list[str], cwd: Path, timeout: int) -> tuple[int, bytes, bytes, bool, int]:
    """Run a subprocess with timeout and capped output. Returns (rc, out, err, timed_out, elapsed_ms)."""
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


def git_snapshot(cwd: Path) -> dict:
    def run(args: list[str]) -> str:
        try:
            result = subprocess.run(args, cwd=cwd, text=True, capture_output=True,
                                    check=False, timeout=10)
        except subprocess.TimeoutExpired:
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""
    head = run(["git", "rev-parse", "HEAD"])
    status = run(["git", "status", "--porcelain=v1"])
    return {"git_head": head or None, "working_tree_sha256": hashlib.sha256(status.encode()).hexdigest()}


def load_contract(session_dir: Path) -> dict:
    path = session_dir / "contract.json"
    if not path.exists():
        raise ValueError("session has no contract.json; initialize a structured Gravitas contract first")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("contract.json must contain an object")
    return loaded


def validate_invocation(contract: dict, validator_id: str, criterion_ids: list[str], command: list[str]) -> None:
    """Bind runner evidence to the declared validator and acceptance criteria."""
    validators = {item.get("id"): item for item in contract.get("validators", []) if isinstance(item, dict)}
    validator = validators.get(validator_id)
    if not validator:
        raise ValueError(f"validator_id {validator_id!r} is not declared by this contract")
    declared = validator.get("command")
    if not isinstance(declared, list) or not declared or not all(isinstance(part, str) for part in declared):
        raise ValueError(
            f"validator {validator_id!r} must declare its command as a non-empty argv array of strings "
            f"(got {type(declared).__name__}); string-form commands are not supported"
        )
    if command != declared:
        raise ValueError("validator command differs from the contract declaration")

    criteria = {
        item.get("id"): item
        for item in contract.get("acceptance_criteria", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    unknown = sorted(set(criterion_ids) - set(criteria))
    if unknown:
        raise ValueError("unknown structured criterion ID(s): " + ", ".join(unknown))
    allowed_by_validator = set(validator.get("criterion_ids", []))
    if allowed_by_validator and not set(criterion_ids).issubset(allowed_by_validator):
        raise ValueError("criterion ID is not assigned to this validator")
    for criterion_id in criterion_ids:
        assigned = criteria[criterion_id].get("validators", [])
        if assigned and validator_id not in assigned:
            raise ValueError(f"validator {validator_id!r} is not assigned to criterion {criterion_id!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Gravitas-owned validator")
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--validator-id", required=True)
    parser.add_argument("--criterion-id", action="append", default=[])
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="wall-clock bound in seconds for the validator command")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = parser.parse_args()
    if not args.command or args.command[0] != "--":
        parser.error("pass the validator command after --")
    command = args.command[1:]
    if not command:
        parser.error("validator command cannot be empty")
    session_dir, cwd_arg = Path(args.session_dir), args.cwd
    try:
        cwd = confine_cwd(cwd_arg)
    except ValueError as error:
        parser.error(str(error))
    try:
        validate_invocation(load_contract(session_dir), args.validator_id, args.criterion_id, command)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    start = time.monotonic()
    rc, out_b, err_b, timed_out, elapsed_ms = run_bounded(command, cwd, args.timeout)
    stdout_text = out_b.decode("utf-8", errors="replace")
    stderr_text = err_b.decode("utf-8", errors="replace")
    # Durable output is intentionally digest-only; callers can retain verbose logs elsewhere.
    verdict = "FAIL" if (timed_out or rc != 0) else "PASS"
    record = {
        "source": "validator",
        "validator_id": args.validator_id,
        "criterion_ids": args.criterion_id,
        "resolution_ids": resolution_links(
            session_dir, source="validator", criterion_ids=args.criterion_id
        ),
        "command": command,
        "command_sha256": sha256(command),
        "exit_code": rc,
        "stdout_sha256": hashlib.sha256(out_b).hexdigest(),
        "stderr_sha256": hashlib.sha256(err_b).hexdigest(),
        "duration_ms": elapsed_ms,
        "timed_out": timed_out,
        "evidence": f"validator {args.validator_id} {'timed out' if timed_out else f'exited {rc}'}",
        "verdict": verdict,
        **git_snapshot(cwd),
    }
    try:
        saved = append_evidence(session_dir, record)
    except (OSError, ValueError) as error:
        # The validator ran; only its evidence record was lost. Report the
        # loss explicitly (fail-closed: the gate requires the ledger entry)
        # instead of dying with a traceback that breaks the JSON protocol.
        print(json.dumps({"verdict": verdict, "exit_code": rc,
                          "timed_out": timed_out,
                          "evidence_error": f"evidence append failed: {error}"}))
        return 1
    print(json.dumps({"verdict": saved["verdict"], "exit_code": rc,
                      "timed_out": timed_out, "event_hash": saved["event_hash"]}))
    return rc if not timed_out else 124


if __name__ == "__main__":
    raise SystemExit(main())
