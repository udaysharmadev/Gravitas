#!/usr/bin/env python3
"""Adaptive policy engine for the Gravitas runtime.

Policy consumes normalized :class:`Action` objects (see gravitas_action),
never host tool names. Two responsibilities:

1. **Action policy** (:func:`evaluate_action`): allow / deny / force_ask for a
   single action given the session contract and recorded session facts.
2. **Planning policy** (:func:`decide`): choose direct / compact / deep /
   replan and emit a machine-readable record with reason codes. Explicit
   rules, no calibrated weights; GravitasBench data calibrates later.

Mode vocabulary (unified; old ``plan-only``/``review-only`` accepted as
aliases for migration):

- read-only: answer, research, plan, review, security-review
- mutating: implement, debug, migration
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from gravitas_action import (
    LEVELS,
    Action,
    HostEnvelope,
    canonical_path,
    case_insensitive_fs,
    normalize,
    path_key,
    workspace_roots,
)

MODES = frozenset({
    "answer", "research", "plan", "review", "security-review",
    "implement", "debug", "migration",
})

READ_ONLY_MODES = frozenset({"answer", "research", "plan", "review", "security-review"})

MODE_ALIASES = {"plan-only": "plan", "review-only": "review"}


# Unknown, empty, or non-string modes must not buy write access: they fall back
# to the most restrictive read-only mode. A missing "mode" key is a separate
# case, handled by callers via ``contract.get("mode", "implement")``.
FAIL_CLOSED_MODE = "answer"


def normalize_mode(mode: object) -> str:
    if not isinstance(mode, str):
        return FAIL_CLOSED_MODE
    mode = mode.strip().lower()
    mode = MODE_ALIASES.get(mode, mode)
    return mode if mode in MODES else FAIL_CLOSED_MODE


def action_fingerprint(tool: str, args: dict) -> str:
    key = json.dumps({"tool": tool, "input": args}, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _path_is_within_scope(candidate: Path, scope: Path, *, case_insensitive: bool) -> bool:
    """Compare concrete paths with a boundary-aware string check.

    ``Path.relative_to`` follows the host filesystem semantics, which makes it
    impossible to enforce a deliberate ``case_insensitive=False`` check on a
    case-folding volume. The scope guard must therefore compare the folded path
    strings directly and require a directory boundary (slash or backslash)
    before a descendant match.
    """
    candidate_key = path_key(candidate, case_insensitive=case_insensitive).replace("\\", "/")
    scope_key = path_key(scope, case_insensitive=case_insensitive).replace("\\", "/").rstrip("/")
    if not scope_key:
        return True
    return candidate_key == scope_key or candidate_key.startswith(scope_key + "/")


def target_in_scope(target: str, scopes: list, roots: list[Path], *,
                    case_insensitive: bool | None = None) -> bool:
    """Both sides go through canonical_path + path_key: ``..`` and symlink
    escapes resolve before comparison, and case folds only when the scope's
    own volume folds (roots and absolute scopes may sit on different ones)."""
    candidates = {canonical_path(target, [root]) for root in roots}
    lexical_candidates = set()
    if case_insensitive is False:
        for root in roots:
            text = target.replace("\\", "/") if os.name == "nt" else target
            path = Path(text)
            if not path.is_absolute():
                path = root / path
            lexical_candidates.add(path.absolute())

    for scope in scopes:
        if not isinstance(scope, str) or not scope:
            continue
        for root in roots:
            scope_path = canonical_path(scope, [root])
            fold = case_insensitive_fs(scope_path) if case_insensitive is None else case_insensitive
            scope_parts = Path(path_key(scope_path, case_insensitive=fold)).parts
            if lexical_candidates:
                scope_text = scope.replace("\\", "/") if os.name == "nt" else scope
                lexical_scope = Path(scope_text)
                if not lexical_scope.is_absolute():
                    lexical_scope = root / lexical_scope
                lexical_scope_parts = lexical_scope.absolute().parts
                if not any(
                    len(candidate.parts) >= len(lexical_scope_parts)
                    and candidate.parts[:len(lexical_scope_parts)] == lexical_scope_parts
                    for candidate in lexical_candidates
                ):
                    continue
            for candidate in candidates:
                if _path_is_within_scope(candidate, scope_path, case_insensitive=fold):
                    return True
    return False


def evaluate_action(action: Action, *, mode: str, allowed_scope: list,
                    reads: set, failed_fingerprints: set,
                    roots: list[Path], fingerprint: str) -> tuple[str, str]:
    """Return (decision, reason) for one normalized action.

    Decisions: ``allow`` | ``deny`` | ``force_ask``.
    """
    mode = normalize_mode(mode)

    # 1. Action lock: read-only modes deny writes and all shell execution
    #    that is not a provably read-only query.
    if action.tool in ("write_to_file", "replace_file_content", "multi_replace_file_content") or action.mutation != "none":
        if mode in READ_ONLY_MODES:
            return ("deny",
                    f"Action lock: mode={mode} does not permit {action.tool}. "
                    f"Task contract mode '{mode}' is read-only. "
                    f"To perform writes, change the task mode to 'implement'.")

    # 2. Write scope guard (dedicated file-edit tools).
    if allowed_scope and action.kind == "write":
        target = action.paths[0] if action.paths else ""
        if target and not target_in_scope(target, allowed_scope, roots):
            return ("deny",
                    f"Scope violation: {target} is outside allowed_write_scope {allowed_scope}. "
                    f"Update the task contract to include this path if the write is intentional.")

    # 2b. Enumerable shell writes obey the same scope. Only paths the
    # runtime can enumerate (redirects, tee/dd operands) are checked;
    # code-execution side effects are governed by capability level, and
    # TOCTOU races between check and execution are a documented limit.
    if allowed_scope and action.kind in ("execute", "network") and action.paths and action.mutation != "none":
        stray = [path for path in action.paths
                 if not target_in_scope(path, allowed_scope, roots)]
        if stray:
            return ("deny",
                    f"Scope violation: shell writes to {stray} outside allowed_write_scope {allowed_scope}. "
                    f"Update the task contract to include these paths if the writes are intentional.")

    # 3. Destructive operations require explicit host-side confirmation.
    if action.mutation == "destructive":
        return ("force_ask", "Destructive operation requires explicit user confirmation.")

    # 4. Read-before-write check.
    if action.kind == "write" and action.paths:
        # Ledger rows may predate record-time canonicalization, so both
        # sides are canonicalized here; exists() uses the unfolded path.
        target_path = canonical_path(action.paths[0], roots)
        fold = case_insensitive_fs(target_path)
        read_keys = {path_key(canonical_path(item, roots), case_insensitive=fold) for item in reads}
        if target_path.exists() and path_key(target_path, case_insensitive=fold) not in read_keys:
            return ("deny",
                    f"Read-before-write violation: {action.paths[0]} has not been read this session. "
                    f"Read the file before editing it (Rule 1).")

    # 5. Duplicate failed action prevention.
    if fingerprint in failed_fingerprints:
        return ("deny",
                "Duplicate failed action: this exact operation failed previously this session. "
                "Check failures.jsonl for the reason. Try a different approach.")

    return ("allow", "")


# ---------------------------------------------------------------------------
# Planning policy.
# ---------------------------------------------------------------------------

PLANNING_LEVELS = ("direct", "compact", "deep", "replan")
CONTEXT_DEPTHS = ("target", "dependency", "subsystem")
VERIFICATION_DEPTHS = ("targeted", "impact", "full")
DELEGATIONS = ("none", "investigator", "reviewer", "impact-auditor", "test-adversary")


def _safe_int(value: object, default: int = 0) -> int:
    """Coerce signal counts without crashing on strings/None/bools."""
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def decide(signals: dict) -> dict:
    """Choose planning / context / verification / delegation from signals.

    ``signals`` keys (all optional, explicit booleans/ints):
      read_only, trivial, destructive, security, auth, migration,
      dependent_files, shared_module, broad_fanout, uncertainty
      ("low"|"medium"|"high"), files (int), repeated_failures (int),
      assumptions_invalidated, scope_expanded, validator_failure,
      localization_uncertain, independent_workstreams (int), strict (bool).

    Returns a JSON-serializable record with reason codes, never prose.
    """
    if not isinstance(signals, dict):
        signals = {}
    uncertainty = signals.get("uncertainty", "low")
    repeated = _safe_int(signals.get("repeated_failures", 0))
    files = _safe_int(signals.get("files", 1), default=1)
    if files < 1:
        files = 1
    high_stakes = bool(signals.get("destructive") or signals.get("security")
                       or signals.get("auth") or signals.get("migration")
                       or signals.get("broad_fanout"))
    reason_codes: list[str] = []

    if signals.get("read_only") or signals.get("trivial"):
        # Trivial/read-only fast-path yields to high-stakes signals: a
        # "trivial" label must never buy minimal planning for destructive,
        # security, auth, or migration work.
        if not high_stakes:
            reason_codes.append("read-only-or-trivial" if signals.get("read_only") else "trivial-localized")
            return _with_delegation(
                _record("direct", "target", "targeted", "none", reason_codes),
                signals, high_stakes=high_stakes)

    if (signals.get("assumptions_invalidated") or signals.get("scope_expanded")
            or repeated >= 2 or signals.get("validator_failure") == "diagnosis-changed"):
        if signals.get("assumptions_invalidated"):
            reason_codes.append("assumptions-invalidated")
        if signals.get("scope_expanded"):
            reason_codes.append("scope-expanded")
        if repeated >= 2:
            reason_codes.append("repeated-failure")
        if signals.get("validator_failure") == "diagnosis-changed":
            reason_codes.append("validator-changed-diagnosis")
        return _with_delegation(
            _record("replan", "dependency", "impact", "none", reason_codes),
            signals, high_stakes=high_stakes)

    if high_stakes or uncertainty == "high":
        for key in ("destructive", "security", "auth", "migration", "broad_fanout"):
            if signals.get(key):
                reason_codes.append(key.replace("_", "-"))
        if uncertainty == "high":
            reason_codes.append("high-uncertainty")
        return _with_delegation(
            _record("deep", "subsystem", "full" if high_stakes else "impact", "none", reason_codes),
            signals, high_stakes=high_stakes)

    if signals.get("dependent_files") or signals.get("shared_module") or files > 1 or uncertainty == "medium":
        for key in ("dependent_files", "shared_module"):
            if signals.get(key):
                reason_codes.append(key.replace("_", "-"))
        if files > 1:
            reason_codes.append("multiple-files")
        if uncertainty == "medium":
            reason_codes.append("medium-uncertainty")
        return _with_delegation(
            _record("compact", "dependency", "impact", "none", reason_codes),
            signals, high_stakes=False)

    reason_codes.append("single-file-low-uncertainty")
    return _with_delegation(
        _record("direct", "target", "targeted", "none", reason_codes),
        signals, high_stakes=high_stakes)


def _record(planning: str, context_depth: str, verification_depth: str,
            delegation: str, reason_codes: list[str]) -> dict:
    return {
        "planning": planning,
        "context_depth": context_depth,
        "verification_depth": verification_depth,
        "delegation": delegation,
        "reason_codes": sorted(set(reason_codes)),
    }


def _with_delegation(record: dict, signals: dict, *, high_stakes: bool) -> dict:
    """Merge delegation choice into a decide() record without dropping codes."""
    extra = _delegation(signals, high_stakes=high_stakes)
    if not extra:
        return record
    record["delegation"] = extra["delegation"]
    record["reason_codes"] = sorted(set(record["reason_codes"]) | set(extra.get("reason_codes", [])))
    return record


def _delegation(signals: dict, *, high_stakes: bool) -> dict:
    if signals.get("localization_uncertain"):
        return {"delegation": "investigator", "reason_codes": ["localization-uncertain"]}
    if signals.get("strict") and signals.get("security"):
        return {"delegation": "test-adversary", "reason_codes": ["strict-security"]}
    if high_stakes and (signals.get("broad_fanout") or _safe_int(signals.get("files", 1), default=1) > 3):
        return {"delegation": "impact-auditor", "reason_codes": ["blast-radius-uncertain"]}
    if high_stakes:
        return {"delegation": "reviewer", "reason_codes": ["risky-implementation"]}
    if _safe_int(signals.get("independent_workstreams", 1), default=1) > 1:
        return {"delegation": "none",
                "reason_codes": ["parallel-workstreams-require-explicit-split"]}
    return {}


def policy_record_for_contract(contract: dict, signals: dict) -> dict:
    """Attach mode/policy context to a decide() record for auditability."""
    record = decide(signals)
    record["mode"] = normalize_mode(contract.get("mode", "implement"))
    record["policy_dimensions"] = {
        key: contract.get("policy", {}).get(key) if isinstance(contract.get("policy"), dict) else None
        for key in ("action_risk", "reversibility", "uncertainty", "blast_radius", "verification_depth")
    }
    return record


__all__ = [
    "MODES", "READ_ONLY_MODES", "MODE_ALIASES", "FAIL_CLOSED_MODE", "normalize_mode",
    "action_fingerprint", "target_in_scope", "evaluate_action",
    "decide", "policy_record_for_contract", "normalize", "workspace_roots",
    "Action", "HostEnvelope",
]
