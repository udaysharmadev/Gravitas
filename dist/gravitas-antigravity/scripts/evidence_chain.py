"""Append-only, hash-linked evidence records with user-local head anchors.

Anchors detect project-ledger rewrites only while the per-user anchor directory
remains outside the attacker-controlled write scope; they do not authenticate
against a same-user process that can rewrite both locations.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _session_key(session_dir: Path) -> str:
    return hashlib.sha256(str(session_dir.resolve()).encode("utf-8")).hexdigest()


def anchor_path(session_dir: Path) -> Path:
    """Resolve the user-local anchor outside the project/session directory."""
    return Path.home() / ".gravitas" / "anchors" / f"{_session_key(session_dir)}.jsonl"


def _parse_anchor_records(content: str, session_key: str) -> tuple[list[dict], str | None]:
    records = []
    previous_hash = None
    for line_number, line in enumerate(content.splitlines(), 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return [], f"anchor line {line_number} is not JSON"
        if not isinstance(record, dict):
            return [], f"anchor line {line_number} is not an object"
        anchor_hash = record.pop("anchor_hash", None)
        if (record.get("session_key") != session_key
                or record.get("sequence") != line_number
                or record.get("previous_anchor_hash") != previous_hash
                or not isinstance(record.get("ledger_head"), str)
                or sha256(record) != anchor_hash):
            return [], f"anchor line {line_number} is invalid"
        record["anchor_hash"] = anchor_hash
        records.append(record)
        previous_hash = anchor_hash
    return records, None


def _anchor_records(path: Path, session_key: str) -> tuple[list[dict], str | None]:
    if not path.exists():
        return [], None
    return _parse_anchor_records(path.read_text(encoding="utf-8"), session_key)


#: Upgrade hint embedded in the unanchored-head deficit so pre-anchor
#: ledgers get a migration path instead of a bare failure.
BACKFILL_COMMAND = "gravitas verify --backfill-anchors --session-dir <session-dir>"


def _hashed_entries(ledger_path: Path) -> list[dict]:
    """Load ledger records that carry an event hash; skip anything else."""
    entries = []
    if not ledger_path.exists():
        return entries
    with ledger_path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict) and isinstance(entry.get("event_hash"), str):
                entries.append(entry)
    return entries


def _mark_anchor_pending(path: Path, event_hash: str, error: str) -> dict | None:
    """Flag the just-appended record when its anchor write failed.

    The ledger entry is already durable; rewriting its last line to carry
    ``anchor_pending: true`` keeps the failure visible to verification
    (fail-closed) without raising into hook/validator callers. The hash is
    recomputed over the flagged record so the chain stays internally valid.
    Returns the patched record, or None when the patch itself failed.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    index = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].strip()), None)
    if index is None:
        return None
    try:
        record = json.loads(lines[index])
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict) or record.get("event_hash") != event_hash:
        # Another process appended after us; leave its record untouched.
        return None
    record["anchor_pending"] = True
    record["anchor_error"] = error[:200]
    record.pop("event_hash", None)
    record["event_hash"] = sha256(record)
    lines[index] = canonical_json(record)
    try:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        return None
    return record


def _append_anchor(session_dir: Path, ledger_head: str) -> None:
    key = _session_key(session_dir)
    path = anchor_path(session_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(path.parent, 0o700)
        if stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
            raise OSError(f"could not secure anchor directory: {path.parent}")
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_RDWR, 0o600)
    if os.name != "nt":
        os.chmod(path, 0o600)
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            os.close(descriptor)
            raise OSError(f"could not secure anchor file: {path}")
    with os.fdopen(descriptor, "a+", encoding="utf-8") as handle:
        handle.seek(0)
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        try:
            import msvcrt
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        except (ImportError, OSError):
            pass
        try:
            handle.seek(0)
            records, error = _parse_anchor_records(handle.read(), key)
            if error:
                raise ValueError(error)
            record = {
                "session_key": key,
                "sequence": len(records) + 1,
                "ledger_head": ledger_head,
                "previous_anchor_hash": records[-1]["anchor_hash"] if records else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            record["anchor_hash"] = sha256(record)
            handle.seek(0, os.SEEK_END)
            handle.write(canonical_json(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (NameError, OSError):
                pass
            try:
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except (NameError, OSError):
                pass


def resolution_links(
    session_dir: Path,
    *,
    source: str,
    file: str | None = None,
    criterion_ids: list[str] | None = None,
) -> list[str]:
    """Link post-resolution evidence to the failures it helps close."""
    path = session_dir / "failures.jsonl"
    if not path.exists():
        return []
    latest_by_fingerprint = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        fingerprint = entry.get("fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            latest_by_fingerprint[fingerprint] = entry

    links = []
    for marker in latest_by_fingerprint.values():
        if marker.get("resolved") is not True:
            continue
        identifier = marker.get("resolution_id", marker.get("fingerprint"))
        if not isinstance(identifier, str):
            continue
        if source == "read":
            targets = marker.get("required_reads", ["*"])
            if not isinstance(targets, list):
                targets = ["*"]
            matches_file = file and any(
                target == "*"
                or (
                    isinstance(target, str)
                    and os.path.normcase(os.path.abspath(target))
                    == os.path.normcase(os.path.abspath(file))
                )
                for target in targets
            )
            if not matches_file:
                continue
        elif source == "validator":
            required = marker.get("criterion_ids", [])
            if not isinstance(required, list) or not set(required).intersection(criterion_ids or []):
                continue
        else:
            continue
        links.append(identifier)
    return sorted(set(links))


def resolution_records(evidence: list) -> dict[str, dict]:
    """Index hash-linked failure-resolution entries by their resolution ID."""
    return {
        entry["resolution_id"]: entry
        for entry in evidence
        if isinstance(entry, dict)
        and entry.get("source") == "failure_resolution"
        and isinstance(entry.get("resolution_id"), str)
        and entry.get("resolution_id")
        and isinstance(entry.get("event_hash"), str)
    }


def resolution_matches(marker: dict, record: dict | None) -> bool:
    """Bind the mutable failure-log marker to its anchored ledger record."""
    if not record or marker.get("resolved") is not True:
        return False
    return all(
        marker.get(field) == record.get(field)
        for field in (
            "fingerprint", "resolution_id", "reason", "timestamp",
            "required_reads", "criterion_ids",
        )
    )


def verified_resolution_records(session_dir: Path) -> dict[str, dict]:
    """Return resolution records only when the ledger still verifies to its anchor."""
    valid, _ = verify_with_anchor(session_dir)
    if not valid:
        return {}
    path = session_dir / "evidence.jsonl"
    evidence = []
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    evidence.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return resolution_records(evidence)


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
    """Atomically append a timestamped, hash-linked record on POSIX hosts.

    The ledger append is durable first; the user-local anchor follows. An
    anchor-store failure (read-only home, unsecurable directory, corrupt
    anchor file) never raises: the entry is flagged ``anchor_pending`` so
    verification and the stop gate stay fail-closed while hooks keep
    running without tracebacks.
    """
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
    try:
        _append_anchor(session_dir, record["event_hash"])
    except (OSError, ValueError) as error:
        patched = _mark_anchor_pending(path, record["event_hash"], str(error))
        if patched is not None:
            return patched
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


def verify_with_anchor(session_dir: Path) -> tuple[bool, str]:
    """Require every externally anchored head and the current ledger head to match.

    Fail-closed throughout: a broken anchor store, a pending anchor, or an
    unanchored head all report a deficit (never a traceback), so breaking
    the anchor directory blocks completion instead of allowing it. Pending
    flags covered by a later anchor need no deficit: the hash chain commits
    the whole prefix to the anchored head.
    """
    ledger_path = session_dir / "evidence.jsonl"
    valid, reason = verify_chain(ledger_path)
    if not valid:
        return valid, reason

    entries = _hashed_entries(ledger_path)
    if not entries:
        return True, "no anchored evidence"

    ledger_heads = [entry["event_hash"] for entry in entries]
    key = _session_key(session_dir)
    try:
        anchors, error = _anchor_records(anchor_path(session_dir), key)
    except OSError as error:
        return False, (f"anchor store unreadable ({error}); completion blocked "
                       "until the anchor directory is readable again")
    if error:
        return False, error
    if not anchors:
        if any(entry.get("anchor_pending") for entry in entries):
            return False, ("anchor pending — the anchor store write failed; "
                           "re-run verify once the anchor directory is writable")
        return False, ("ledger head not anchored — this ledger predates anchoring; "
                       f"run `{BACKFILL_COMMAND}` on this trusted ledger to anchor its head")
    head_index = 0
    for anchor in anchors:
        try:
            head_index = ledger_heads.index(anchor["ledger_head"], head_index) + 1
        except ValueError:
            return False, "anchored head missing from evidence ledger"
    if anchors[-1]["ledger_head"] != ledger_heads[-1]:
        tail = entries[head_index:]
        if any(entry.get("anchor_pending") for entry in tail):
            return False, ("anchor pending — the anchor store write failed; "
                           "re-run verify once the anchor directory is writable")
        return False, "ledger head not anchored (latest anchor does not match the ledger head)"
    return True, "chain valid; ledger head anchored"


def backfill_anchors(session_dir: Path) -> tuple[bool, str]:
    """Anchor the current head of a pre-existing ledger into the local chain.

    Upgrade path for ledgers written before anchoring existed: verify the
    hash chain, then append an anchor for the current head. Only run this
    on a ledger you trust — anchoring legitimizes whatever the head
    commits to. A broken chain or a corrupt anchor chain refuses
    (fail-closed) instead of resetting history.
    """
    ledger_path = session_dir / "evidence.jsonl"
    valid, reason = verify_chain(ledger_path)
    if not valid:
        return False, reason
    entries = _hashed_entries(ledger_path)
    if not entries:
        return True, "no anchored evidence"
    key = _session_key(session_dir)
    try:
        anchors, error = _anchor_records(anchor_path(session_dir), key)
    except OSError as error:
        return False, (f"anchor store unreadable ({error}); completion blocked "
                       "until the anchor directory is readable again")
    if error:
        return False, error
    if anchors and anchors[-1]["ledger_head"] == entries[-1]["event_hash"]:
        return True, "chain valid; ledger head anchored"
    try:
        _append_anchor(session_dir, entries[-1]["event_hash"])
    except (OSError, ValueError) as error:
        return False, (f"anchor backfill failed ({error}); "
                       "re-run once the anchor directory is writable")
    return True, "chain valid; ledger head anchored"
