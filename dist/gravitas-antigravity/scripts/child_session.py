#!/usr/bin/env python3
"""Scoped child (subagent) sessions for the Gravitas runtime.

Delegation is conditional and bounded: a child session derives its contract
from its parent, never the other way around.

Invariants enforced here (not just in prose):
1. Scope containment: every child ``allowed_write_scope`` entry must be
   inside (equal to or under) a parent scope entry. A read-only child
   delegates with an empty scope.
2. No mode escalation: a child of a read-only parent (answer, research,
   plan, review, security-review) cannot use a mutating mode (implement,
   debug, migration).
3. Criteria subset: delegated acceptance-criteria ids must exist in the
   parent contract.
4. Handoff before credit: a parent may only mark delegated criteria
   complete when the child session's own evidence shows fresh PASS for
   them. The parent stop gate blocks ``allow`` while registered children
   are incomplete.

Violations raise ValueError (fail-closed at delegation time).
"""
from __future__ import annotations

import json
from pathlib import Path

from gravitas_action import canonical_path
from gravitas_evidence import criterion_states
from gravitas_policy import MODES, MODE_ALIASES, READ_ONLY_MODES, normalize_mode


def parent_criterion_ids(contract: dict) -> list[str]:
    """Ids of the parent contract's acceptance criteria, in order."""
    ids = []
    for index, criterion in enumerate(contract.get("acceptance_criteria", []), 1):
        if isinstance(criterion, dict) and criterion.get("id"):
            ids.append(str(criterion["id"]))
        else:
            ids.append(f"AC{index}")
    return ids


def _scope_contains(parent_scope: list, child_entry: str, roots: list[Path]) -> bool:
    """True when child_entry is inside (or equal to) some parent entry."""
    try:
        child = canonical_path(child_entry, roots)
    except (OSError, ValueError):
        return False
    for entry in parent_scope:
        if not isinstance(entry, str) or not entry:
            continue
        try:
            parent = canonical_path(entry, roots)
        except (OSError, ValueError):
            continue
        if child == parent:
            return True
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            continue
    return False


def derive_child_contract(
    parent_contract: dict,
    *,
    scope: list,
    criteria: list,
    mode: str,
    objective: str = "",
    parent_session: str = "",
) -> dict:
    """Derive a validated child contract from its parent.

    Raises ValueError on scope escape, mode escalation, unknown criteria,
    or an unusable parent contract.
    """
    if not isinstance(parent_contract, dict):
        raise ValueError("parent contract must be a JSON object")
    parent_mode = normalize_mode(parent_contract.get("mode", "implement"))
    child_mode = normalize_mode(mode)
    if parent_mode in READ_ONLY_MODES and child_mode not in READ_ONLY_MODES:
        raise ValueError(
            f"mode escalation denied: read-only parent ({parent_mode}) "
            f"cannot delegate mutating mode ({child_mode})"
        )
    if not isinstance(scope, list):
        raise ValueError("child scope must be a list")
    parent_scope = parent_contract.get("allowed_write_scope", [])
    if not isinstance(parent_scope, list):
        raise ValueError("parent allowed_write_scope must be a list")
    roots = [Path.cwd().resolve()]
    for entry in scope:
        if not isinstance(entry, str) or not entry:
            raise ValueError("child scope entries must be non-empty strings")
        if entry not in parent_scope and not _scope_contains(parent_scope, entry, roots):
            raise ValueError(f"child scope escapes parent scope: {entry!r}")
    available = parent_criterion_ids(parent_contract)
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("child criteria must be a non-empty list of parent criterion ids")
    for identifier in criteria:
        if identifier not in available:
            raise ValueError(f"child criterion {identifier!r} is not in the parent contract")
    child = {
        "mode": child_mode,
        "objective": objective or f"Delegated work from parent session {parent_session or 'unknown'}",
        "acceptance_criteria": [
            {"id": identifier, "statement": f"Delegated: {identifier}"} for identifier in criteria
        ],
        "allowed_write_scope": list(scope),
        "budget": parent_contract.get("budget", "balanced"),
        "parent_session": parent_session,
    }
    return child


def load_state(session_dir: Path) -> dict:
    state_path = session_dir / "state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return state if isinstance(state, dict) else {}
    return {}


def save_state(session_dir: Path, state: dict) -> None:
    (session_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def register_child(parent_session_dir: Path, child_key: str, criteria: list) -> dict:
    """Record a delegated child in the parent state. Child starts incomplete."""
    state = load_state(parent_session_dir)
    children = state.get("child_sessions")
    if not isinstance(children, list):
        children = []
        state["child_sessions"] = children
    if any(isinstance(item, dict) and item.get("key") == child_key for item in children):
        raise ValueError(f"child session {child_key!r} is already registered")
    children.append({"key": child_key, "criteria": list(criteria), "status": "incomplete"})
    save_state(parent_session_dir, state)
    return state


def load_evidence(session_dir: Path) -> list:
    evidence_path = session_dir / "evidence.jsonl"
    if not evidence_path.exists():
        return []
    entries = []
    for line in evidence_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def complete_child_handoff(parent_session_dir: Path, child_session_dir: Path, criteria: list) -> dict:
    """Mark a child complete only when the child's own evidence covers criteria.

    Reads the child contract + evidence ledger, requires fresh PASS for every
    delegated criterion, then flips the parent registration to complete.
    Raises ValueError when the handoff is not yet earned.
    """
    contract_path = child_session_dir / "contract.json"
    try:
        child_contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"child contract unreadable: {error}") from error
    if not isinstance(child_contract, dict):
        raise ValueError("child contract must be a JSON object")
    states = criterion_states(child_contract, load_evidence(child_session_dir))
    uncovered = [identifier for identifier in criteria if states.get(identifier, {}).get("status") != "PASS"]
    if uncovered:
        raise ValueError(f"child has no fresh PASS for: {', '.join(uncovered)}")
    state = load_state(parent_session_dir)
    children = state.get("child_sessions")
    child_key = child_session_dir.name
    if isinstance(children, list):
        for item in children:
            if isinstance(item, dict) and item.get("key") == child_key:
                item["status"] = "complete"
                item["criteria"] = list(criteria)
                save_state(parent_session_dir, state)
                return state
    raise ValueError(f"child session {child_key!r} is not registered with this parent")


def incomplete_children(parent_session_dir: Path) -> list:
    """Keys of registered children not yet handed off as complete."""
    state = load_state(parent_session_dir)
    children = state.get("child_sessions")
    if not isinstance(children, list):
        return []
    return [
        str(item.get("key")) for item in children
        if isinstance(item, dict) and item.get("status") != "complete" and item.get("key")
    ]
