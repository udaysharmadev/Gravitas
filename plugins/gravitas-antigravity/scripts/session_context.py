"""Conversation-scoped session lookup shared by Gravitas runtime hooks.

Antigravity hooks may include ``conversationId``.  The runtime hashes that value
for its on-disk directory name so concurrent conversations cannot select the
newest unrelated session and the raw host identifier is not written to disk.
"""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path


SESSION_ROOT = Path(".gravitas") / "sessions"


def conversation_key(payload: object) -> str | None:
    """Return a stable, filesystem-safe key for an official host conversation ID."""
    if not isinstance(payload, dict):
        return None
    raw = payload.get("conversationId") or payload.get("conversation_id")
    if not isinstance(raw, str) or not raw:
        return None
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"conversation-{digest}"


def session_dir_for_payload(payload: object, *, create: bool = False) -> Path | None:
    """Resolve a conversation-scoped session, falling back only for legacy input.

    A payload that carries a conversation ID never falls back to another session.
    This is the isolation property required for concurrent conversations.
    """
    key = conversation_key(payload)
    if key:
        candidate = SESSION_ROOT / key
        if create:
            candidate.mkdir(parents=True, exist_ok=True)
        return candidate if candidate.is_dir() else None

    if not SESSION_ROOT.exists():
        if not create:
            return None
        key = f"legacy-{date.today().isoformat()}"
        candidate = SESSION_ROOT / key
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    sessions = sorted(
        (path for path in SESSION_ROOT.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if sessions:
        return sessions[0]
    if create:
        candidate = SESSION_ROOT / f"legacy-{date.today().isoformat()}"
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    return None
