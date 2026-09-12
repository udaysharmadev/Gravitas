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
import time
from pathlib import Path

from evidence_chain import append_evidence, sha256


def git_snapshot(cwd: Path) -> dict:
    def run(args: list[str]) -> str:
        result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
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
    if command != validator.get("command"):
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
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = parser.parse_args()
    if not args.command or args.command[0] != "--":
        parser.error("pass the validator command after --")
    command = args.command[1:]
    if not command:
        parser.error("validator command cannot be empty")
    session_dir, cwd = Path(args.session_dir), Path(args.cwd).resolve()
    try:
        validate_invocation(load_contract(session_dir), args.validator_id, args.criterion_id, command)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    start = time.monotonic()
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    elapsed_ms = round((time.monotonic() - start) * 1000)
    # Durable output is intentionally digest-only; callers can retain verbose logs elsewhere.
    record = {
        "source": "validator",
        "validator_id": args.validator_id,
        "criterion_ids": args.criterion_id,
        "command": command,
        "command_sha256": sha256(command),
        "exit_code": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
        "duration_ms": elapsed_ms,
        "evidence": f"validator {args.validator_id} exited {result.returncode}",
        "verdict": "PASS" if result.returncode == 0 else "FAIL",
        **git_snapshot(cwd),
    }
    saved = append_evidence(session_dir, record)
    print(json.dumps({"verdict": saved["verdict"], "exit_code": result.returncode, "event_hash": saved["event_hash"]}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
