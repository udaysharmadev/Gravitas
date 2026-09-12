#!/usr/bin/env python3
"""Validate GravitasBench episode files and their derived truth fields."""
import argparse
import json
import sys
from pathlib import Path

def episode_errors(episode, schema, schema_validator=None):
    if not isinstance(episode, dict):
        return ["episode must be a JSON object; aggregate arrays are not episode files"]
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
    parser.add_argument("--allow-empty", action="store_true", help="succeed when the directory has no episode files")
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
    skipped = 0
    for path in paths:
        payload = json.loads(path.read_text())
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
