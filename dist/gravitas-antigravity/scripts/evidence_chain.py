"""Append-only, hash-linked evidence records for the Gravitas runtime.

This is tamper-evident rather than tamper-proof: a writer with filesystem access
can rewrite a ledger.  The chain makes accidental corruption and undisclosed
edits detectable by ``gravitas verify``.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _last_event_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    last = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict) and isinstance(entry.get("event_hash"), str):
                last = entry["event_hash"]
    return last


def append_evidence(session_dir: Path, entry: dict) -> dict:
    """Atomically append a timestamped, hash-linked record on POSIX hosts."""
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_dir / "evidence.jsonl"
    path.touch(exist_ok=True)
    # Advisory locking serializes competing hook processes on macOS/Linux.
    with path.open("a+", encoding="utf-8") as handle:
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        previous = _last_event_hash(path)
        record = dict(entry)
        record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        record["previous_event_hash"] = previous
        hashed = dict(record)
        record["event_hash"] = sha256(hashed)
        handle.write(canonical_json(record) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except (NameError, OSError):
            pass
    return record


def verify_chain(path: Path) -> tuple[bool, str]:
    """Verify all records that opt into the chain; legacy records remain valid."""
    previous = None
    if not path.exists():
        return True, "empty ledger"
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return False, f"line {line_number} is not JSON"
            if "event_hash" not in entry:
                continue
            recorded_hash = entry.pop("event_hash")
            recorded_previous = entry.get("previous_event_hash")
            if recorded_previous != previous:
                return False, f"line {line_number} has an unexpected previous_event_hash"
            if not isinstance(recorded_hash, str) or sha256(entry) != recorded_hash:
                return False, f"line {line_number} hash mismatch"
            previous = recorded_hash
    return True, "chain valid"
