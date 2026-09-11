#!/usr/bin/env python3
"""Validate GravitasBench episode files and their derived truth fields."""
import argparse
import json
import sys
from pathlib import Path

def episode_errors(episode, schema, schema_validator=None):
    errors = [error.message for error in schema_validator(schema).iter_errors(episode)] if schema_validator else []
    results = [item["result"] for item in episode.get("validator_outputs", [])]
    solved = bool(results) and all(result == "PASS" for result in results)
    expected = {
        "functional_solve": solved,
        "false_completion": bool(episode.get("claimed_success")) and not solved,
    }
    for field, value in expected.items():
        if field in episode and episode[field] != value:
            errors.append(f"{field} must be {value!r} from validator outputs")
    if episode.get("infrastructure_failure") and any(result == "FAIL" for result in results):
        errors.append("infrastructure failures must use INVALID validator results")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", required=True)
    parser.add_argument("--schema", default=str(Path(__file__).parents[2] / "schemas/episode.schema.json"))
    args = parser.parse_args()
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        print("jsonschema is required: pip install -r benchmarks/runner/requirements.txt", file=sys.stderr)
        return 2
    schema = json.loads(Path(args.schema).read_text())
    paths = sorted(Path(args.episodes).glob("*.json"))
    failures = 0
    for path in paths:
        errors = episode_errors(json.loads(path.read_text()), schema, Draft7Validator)
        if errors:
            failures += 1
            print(f"FAIL {path}: {'; '.join(errors)}")
        else:
            print(f"PASS {path}")
    print(f"Validated {len(paths)} episode(s); {failures} failed")
    return 1 if failures or not paths else 0


if __name__ == "__main__":
    sys.exit(main())
