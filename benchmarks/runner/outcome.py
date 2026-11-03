#!/usr/bin/env python3
"""Canonical benchmark outcomes shared by episode producers and validation.

Every recorded validator is mandatory. Passing hidden tests alone does not
make an episode solved when scope, the step budget, a checkpoint, or any
additional validator fails.
"""
from __future__ import annotations


def derive_outcome(
    tests_passing: bool,
    finished_normally: bool,
    scope_ok: bool,
    infrastructure_failure: bool,
    validators_passing: bool | None = None,
) -> dict:
    """Derive success, preserving callers that predate additional validators."""
    if validators_passing is None:
        validators_passing = bool(
            tests_passing and finished_normally and scope_ok and not infrastructure_failure
        )
    functional_solve = bool(
        tests_passing
        and finished_normally
        and scope_ok
        and validators_passing
        and not infrastructure_failure
    )
    return {
        "tests_passing": bool(tests_passing),
        "finished_normally": bool(finished_normally),
        "scope_ok": bool(scope_ok),
        "infrastructure_failure": bool(infrastructure_failure),
        "validators_passing": bool(validators_passing),
        "functional_solve": functional_solve,
    }


def validators_pass(validator_outputs: list) -> bool:
    """All outputs, including duplicate or additional criteria, must pass."""
    return isinstance(validator_outputs, list) and bool(validator_outputs) and all(
        isinstance(output, dict) and output.get("result") == "PASS"
        for output in validator_outputs
    )


def outcome_from_validators(validator_outputs: list) -> dict | None:
    """Reconstruct implementation components; legacy sets use all-PASS semantics."""
    if not isinstance(validator_outputs, list) or not validator_outputs:
        return None
    by_criterion = {}
    for output in validator_outputs:
        if isinstance(output, dict) and isinstance(output.get("criterion"), str):
            by_criterion.setdefault(output["criterion"], []).append(output.get("result"))
    def passed(criterion):
        results = by_criterion.get(criterion, [])
        return bool(results) and all(result == "PASS" for result in results)

    infrastructure_failure = any(
        isinstance(output, dict) and output.get("result") == "INVALID"
        for output in validator_outputs
    )
    if "Episode finished within step budget" in by_criterion:
        return derive_outcome(
            tests_passing=passed("Hidden acceptance"),
            finished_normally=passed("Episode finished within step budget"),
            scope_ok=passed("Allowed write scope"),
            infrastructure_failure=infrastructure_failure,
            validators_passing=validators_pass(validator_outputs),
        )
    plan = "Plan-only response contains a numbered plan"
    no_tools = "Runner grants no filesystem or shell tools"
    if plan in by_criterion and no_tools in by_criterion:
        return derive_outcome(
            tests_passing=passed(plan),
            finished_normally=not infrastructure_failure,
            scope_ok=all(result != "FAIL" for result in by_criterion[no_tools]),
            infrastructure_failure=infrastructure_failure,
            validators_passing=validators_pass(validator_outputs),
        )
    return None


def expected_derived_fields(validator_outputs: list, claimed_success: bool) -> dict | None:
    """Return the truth fields implied by every recorded validator result."""
    if not isinstance(validator_outputs, list) or not validator_outputs:
        return None
    outcome = outcome_from_validators(validator_outputs)
    if outcome is not None:
        solved = outcome["functional_solve"]
        invalid = outcome["infrastructure_failure"]
    else:
        solved = validators_pass(validator_outputs)
        invalid = any(isinstance(output, dict) and output.get("result") == "INVALID"
                      for output in validator_outputs)
    return {
        "functional_solve": solved,
        "false_completion": bool(claimed_success) and not solved,
        "infrastructure_failure": bool(invalid),
    }
