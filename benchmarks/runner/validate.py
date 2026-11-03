#!/usr/bin/env python3
"""Validate GravitasBench episode files and their derived truth fields."""
import argparse
import json
import sys
from pathlib import Path

def episode_errors(episode, schema, schema_validator=None):
    try:
        from outcome import (
            derive_outcome, expected_derived_fields, outcome_from_validators, validators_pass,
        )
    except ImportError:  # pragma: no cover - script invoked from repo root
        from benchmarks.runner.outcome import (
            derive_outcome, expected_derived_fields, outcome_from_validators, validators_pass,
        )
    if not isinstance(episode, dict):
        return ["episode must be a JSON object; aggregate arrays are not episode files"]
    errors = [error.message for error in schema_validator(schema).iter_errors(episode)] if schema_validator else []
    required_fields = {
        "task_id", "configuration", "validator_outputs", "functional_solve",
        "claimed_success", "false_completion", "infrastructure_failure",
    }
    missing = sorted(required_fields - episode.keys())
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))
    for field in ("task_id", "configuration"):
        if field in episode and (not isinstance(episode[field], str) or not episode[field].strip()):
            errors.append(f"{field} must be a non-empty string")
    for field in ("claimed_success", "functional_solve", "false_completion", "infrastructure_failure"):
        if field in episode and not isinstance(episode[field], bool):
            errors.append(f"{field} must be a boolean")

    outputs = episode.get("validator_outputs")
    if not isinstance(outputs, list):
        errors.append("validator_outputs must be a list")
        outputs = []
    criteria = set()
    for index, output in enumerate(outputs):
        result = output.get("result") if isinstance(output, dict) else None
        if not isinstance(result, str) or result not in {"PASS", "FAIL", "INVALID"}:
            errors.append(f"validator_outputs[{index}].result must be PASS, FAIL, or INVALID")
        if isinstance(output, dict) and "criterion" in output:
            criterion = output["criterion"]
            if not isinstance(criterion, str) or not criterion.strip():
                errors.append(f"validator_outputs[{index}].criterion must be a non-empty string")
            elif criterion in criteria:
                errors.append(f"duplicate validator criterion: {criterion}")
            else:
                criteria.add(criterion)
    if episode.get("simulated_approval") is True and "Tier-2 checkpoint (simulated)" not in criteria:
        errors.append("simulated_approval requires a Tier-2 checkpoint validator")
    expected = expected_derived_fields(outputs, episode.get("claimed_success"))
    if expected is None:
        errors.append("validator_outputs must be a non-empty list")
        return errors
    for field, value in expected.items():
        if field in episode and episode[field] != value:
            errors.append(f"{field} must be {value!r} from validator outputs")
    if "outcome" not in episode:
        return errors
    outcome = episode["outcome"]
    if not isinstance(outcome, dict):
        errors.append("outcome must be an object when present")
        return errors
    component_names = ("tests_passing", "finished_normally", "scope_ok", "infrastructure_failure")
    components = {key: outcome.get(key) for key in component_names}
    for field, value in components.items():
        if not isinstance(value, bool):
            errors.append(f"outcome.{field} must be a boolean")
    for field in ("functional_solve", "validators_passing"):
        if field == "validators_passing" and field not in outcome:
            continue
        if not isinstance(outcome.get(field), bool):
            errors.append(f"outcome.{field} must be a boolean")
    reconstructed = outcome_from_validators(outputs)
    if reconstructed is not None:
        for field in component_names:
            if isinstance(outcome.get(field), bool) and outcome[field] != reconstructed[field]:
                errors.append(f"outcome.{field} must match validator outputs")
    if outcome.get("infrastructure_failure") != expected["infrastructure_failure"]:
        errors.append("outcome.infrastructure_failure must match validator outputs")
    passing = validators_pass(outputs)
    if "validators_passing" in outcome and outcome["validators_passing"] != passing:
        errors.append("outcome.validators_passing must match validator outputs")
    if all(isinstance(value, bool) for value in components.values()):
        check = derive_outcome(**components, validators_passing=passing if reconstructed is not None else None)
        if check["functional_solve"] != expected["functional_solve"]:
            errors.append("outcome components disagree with validator outputs")
    if outcome.get("functional_solve") != expected["functional_solve"]:
        errors.append("outcome.functional_solve must match validator outputs")
    return errors


def read_episode(path):
    """Load one JSON episode and attach its path to parse/read errors."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: unable to read episode JSON: {error}") from error


def validate_episodes(episodes_dir, schema=None, schema_validator=None):
    """Load and check every episode file.

    Every JSON file in this directory must be an episode object. Malformed,
    array-shaped, or schema-invalid files raise ValueError rather than being
    silently omitted. Infrastructure-failure episodes remain in the results
    and are counted as invalid runs downstream. ``schema`` is required:
    calling without a schema would silently accept contradictory
    derived-truth fields.
    """
    if schema is None:
        raise ValueError("episode schema is required for validation")
    episodes, invalid = [], 0
    for path in sorted(Path(episodes_dir).glob("*.json")):
        payload = read_episode(path)
        if isinstance(payload, list):
            raise ValueError(f"{path}: episode must be a JSON object; aggregate arrays are not episode files")
        errors = episode_errors(payload, schema, schema_validator)
        if errors:
            raise ValueError(f"{path}: {'; '.join(errors)}")
        episodes.append(payload)
        if payload.get("infrastructure_failure"):
            invalid += 1
    return episodes, invalid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", required=True)
    parser.add_argument("--allow-empty", action="store_true", help="succeed when the directory has no episode files")
    parser.add_argument("--schema", default=str(Path(__file__).with_name("episode.schema.json")))
    args = parser.parse_args()
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        print("jsonschema is required: pip install -r benchmarks/runner/requirements.txt", file=sys.stderr)
        return 2
    schema = json.loads(Path(args.schema).read_text())
    paths = sorted(Path(args.episodes).glob("*.json"))
    failures = 0
    skipped = 0
    for path in paths:
        try:
            payload = read_episode(path)
        except ValueError as error:
            failures += 1
            print(f"FAIL {error}")
            continue
        if isinstance(payload, list):
            skipped += 1
            print(f"SKIP {path}: aggregate artifact, not an episode")
            continue
        errors = episode_errors(payload, schema, Draft7Validator)
        if errors:
            failures += 1
            print(f"FAIL {path}: {'; '.join(errors)}")
        else:
            print(f"PASS {path}")
    print(f"Validated {len(paths) - skipped} episode(s); {skipped} skipped; {failures} failed")
    return 1 if failures or (not paths and not args.allow_empty) else 0


if __name__ == "__main__":
    sys.exit(main())
