#!/usr/bin/env python3
"""Shared benchmark outcome contract.

Both episode producers (``implementation.py``, ``run.py``) and the
validator (``validate.py``) must agree on what counts as success.
Previously ``implementation`` required ``not error`` while ``validate``
only required all validators PASS, so a step-limit episode with passing
hidden tests disagreed.

Outcome components (all recorded separately):
- tests_passing: hidden acceptance validator passed
- finished_normally: agent reached ``finish`` within the step budget
- scope_ok: no write-scope violation
- infrastructure_failure: provider/timeout failure (INVALID run)
"""
from __future__ import annotations


def derive_outcome(
    tests_passing: bool,
    finished_normally: bool,
    scope_ok: bool,
    infrastructure_failure: bool,
) -> dict:
    """Derive the canonical outcome dict from its four components."""
    functional_solve = bool(
        tests_passing
        and finished_normally
        and scope_ok
        and not infrastructure_failure
    )
    return {
        "tests_passing": bool(tests_passing),
        "finished_normally": bool(finished_normally),
        "scope_ok": bool(scope_ok),
        "infrastructure_failure": bool(infrastructure_failure),
        "functional_solve": functional_solve,
    }


def outcome_from_validators(validator_outputs: list) -> dict | None:
    """Reconstruct outcome components from validator criteria.

    Returns None when the episode uses a legacy validator set without the
    step-budget criterion (e.g. plan-only smoke episodes). Callers must
    fall back to all-PASS semantics in that case.
    """
    if not isinstance(validator_outputs, list) or not validator_outputs:
        return None
    by_criterion = {
        output.get("criterion"): output.get("result")
        for output in validator_outputs
        if isinstance(output, dict)
    }
    if "Episode finished within step budget" not in by_criterion:
        return None
    tests_passing = by_criterion.get("Hidden acceptance") == "PASS"
    finished_normally = by_criterion.get("Episode finished within step budget") == "PASS"
    scope_ok = by_criterion.get("Allowed write scope") == "PASS"
    infrastructure_failure = "INVALID" in list(by_criterion.values())
    return derive_outcome(tests_passing, finished_normally, scope_ok, infrastructure_failure)


def expected_derived_fields(validator_outputs: list, claimed_success: bool) -> dict | None:
    """Return expected functional_solve/false_completion/infrastructure_failure.

    Uses the step-budget-aware outcome when available, else legacy all-PASS.
    Returns None for empty/non-list validator sets (caller reports an error).
    """
    if not isinstance(validator_outputs, list) or not validator_outputs:
        return None
    outcome = outcome_from_validators(validator_outputs)
    if outcome is not None:
        solved = outcome["functional_solve"]
    else:
        results = [
            output.get("result") for output in validator_outputs if isinstance(output, dict)
        ]
        solved = bool(results) and len(results) == len(validator_outputs) and all(
            result == "PASS" for result in results
        )
        outcome = {"infrastructure_failure": "INVALID" in results}
    return {
        "functional_solve": solved,
        "false_completion": bool(claimed_success) and not solved,
        "infrastructure_failure": bool(outcome["infrastructure_failure"]),
    }
