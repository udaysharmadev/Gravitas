#!/usr/bin/env python3
"""Gravitas PreToolUse hook.

Deterministic enforcement before any tool call. Core policy consumes the
normalized action model (gravitas_action) through the policy engine
(gravitas_policy); this file owns Antigravity I/O and session state only.

Order: fail-closed parsing -> uninitialized-conversation guard ->
action lock -> scope guard -> destructive confirm -> read-before-write ->
duplicate-failure guard.

Input (stdin): Antigravity JSON with toolCall.name and toolCall.args
Output (stdout): JSON with decision: allow|deny|force_ask and an optional reason
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from gravitas_action import antigravity_envelope, canonical_path, workspace_roots
from evidence_chain import resolution_matches, verified_resolution_records
from gravitas_policy import (
    MODE_ALIASES,
    MODES,
    READ_ONLY_MODES,
    action_fingerprint,
    evaluate_action,
    normalize,
    normalize_mode,
)
from session_context import session_dir_for_payload


def load_contract(session_dir: Path) -> dict:
    contract_path = session_dir / "contract.json"
    if contract_path.exists():
        with open(contract_path) as f:
            return json.load(f)
    return {}


def load_failures(session_dir: Path) -> list:
    failures_path = session_dir / "failures.jsonl"
    if not failures_path.exists():
        return []
    failures = []
    with open(failures_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    failures.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return failures


def active_failures(failures: list, resolutions: dict) -> list:
    """Apply resolution markers in order so a later failure re-arms its ban."""
    latest_by_fingerprint = {}
    unkeyed = []
    for entry in failures:
        if not isinstance(entry, dict):
            continue
        fingerprint = entry.get("fingerprint")
        if not fingerprint:
            if not resolution_matches(entry, resolutions.get(entry.get("resolution_id"))):
                unkeyed.append(entry)
            continue
        latest_by_fingerprint[fingerprint] = entry
    return unkeyed + [
        entry for entry in latest_by_fingerprint.values()
        if not resolution_matches(entry, resolutions.get(entry.get("resolution_id")))
    ]


def load_reads(session_dir: Path) -> set:
    """Load set of files read this session from evidence ledger."""
    reads = set()
    evidence_path = session_dir / "evidence.jsonl"
    if not evidence_path.exists():
        return reads
    with open(evidence_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    if entry.get("source") == "read" and entry.get("file"):
                        reads.add(entry["file"])
                except json.JSONDecodeError:
                    pass
    return reads


def deny(reason: str):
    print(json.dumps({"decision": "deny", "reason": reason}))


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        deny("Gravitas could not parse the PreToolUse payload; denied fail-closed.")
        return

    envelope, action = antigravity_envelope(payload)
    if envelope is None or action is None:
        deny("Gravitas received a PreToolUse payload without toolCall.name.")
        return

    session_dir = session_dir_for_payload(payload)
    contract = load_contract(session_dir) if session_dir else {}
    raw_mode = contract.get("mode", "implement")
    if raw_mode not in MODES and raw_mode not in MODE_ALIASES:
        deny(f"Unknown contract mode {raw_mode!r}; denied fail-closed.")
        return
    mode = normalize_mode(raw_mode)

    # A native conversation without an initialized contract is deliberately
    # unable to mutate. This prevents one task from inheriting another task's
    # policy via a "latest session" fallback.
    if payload.get("conversationId") and not (session_dir and (session_dir / "contract.json").exists()):
        if action.kind in ("write", "execute", "network"):
            deny("Native session is not initialized with a Gravitas contract; mutations and shell commands fail closed.")
            return

    if action.kind == "write" and not session_dir:
        target = action.paths[0] if action.paths else ""
        if target and canonical_path(target, workspace_roots(envelope)).exists():
            deny("Read-before-write violation: no Gravitas session has recorded a read of this existing file.")
            return

    failures = load_failures(session_dir) if session_dir else []
    reads = load_reads(session_dir) if session_dir else set()
    fingerprint = action_fingerprint(envelope.tool, envelope.args)

    # A resolution re-arms exactly the latest failure for that fingerprint.
    resolutions = {}
    if session_dir and any(
        isinstance(entry, dict) and entry.get("resolved") is True
        for entry in failures
    ):
        resolutions = verified_resolution_records(session_dir)
    failed = {entry.get("fingerprint") for entry in active_failures(failures, resolutions)
              if entry.get("fingerprint")}

    decision, reason = evaluate_action(
        action,
        mode=mode,
        allowed_scope=contract.get("allowed_write_scope", []),
        reads=reads,
        failed_fingerprints=failed,
        roots=workspace_roots(envelope),
        fingerprint=fingerprint,
    )
    if decision == "allow":
        print(json.dumps({"decision": "allow"}))
    elif decision == "force_ask":
        print(json.dumps({"decision": "force_ask", "reason": reason}))
    else:
        deny(reason)


if __name__ == "__main__":
    main()
