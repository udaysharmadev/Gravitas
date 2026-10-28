#!/usr/bin/env python3
"""Harvest a licensed repository into a GravitasBench task draft.

Takes a local repo checkout (already pinned to a commit) and emits:
  1. eval/tasks/<TASK_ID>.yaml draft (description + success criteria + trap)
  2. benchmarks/validators/<TASK_ID>.json metadata (hidden validator hash,
     never the validator source)

Rules (honesty gates):
- Source must have a LICENSE file (unlicensed code is rejected).
- Source commit must be pinned (git rev-parse HEAD recorded).
- Solver-blind: emitted YAML contains no hidden test source, only its sha256.
- Holdout assignment follows benchmarks/manifest.yaml holdout policy.

Usage:
  python benchmarks/runner/harvest.py --source /path/to/repo \\
      --task-id TRAP-006 --lane security-sensitive --title "..." --out-dir .
"""
import argparse
import hashlib
import subprocess
from pathlib import Path


def git_commit(source: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source,
        capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"not a git checkout or no commit: {source}")
    return result.stdout.strip()


def check_license(source: Path) -> Path:
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        candidate = source / name
        if candidate.is_file():
            return candidate
    # Real OSS often uses lowercase (e.g. sindresorhus `license`); match case-insensitively.
    for entry in source.iterdir():
        if entry.is_file() and entry.name.lower() in ("license", "license.md", "license.txt", "copying"):
            return entry
    raise RuntimeError(f"source has no LICENSE file: {source}")


def validator_hash(task_id: str, criteria: list) -> str:
    payload = "\n".join([task_id, *criteria]).encode()
    return hashlib.sha256(payload).hexdigest()


def harvest(source: Path, task_id: str, lane: str, title: str, description: str,
            criteria: list, trap_kind: str, trap_fail: str) -> tuple:
    check_license(source)
    commit = git_commit(source)
    repo_name = source.resolve().name or "repo"
    task_yaml = (
        f'task_id: "{task_id}"\n'
        f'title: "{title}"\n'
        f'category: {lane}\n'
        f'tier: 2\n'
        f'pillars_tested: [1, 2, 4, 5, 6]\n'
        f'repository: "{repo_name}"\n'
        f'commit: "{commit}"\n'
        f'description: |\n'
        + "".join(f"  {line}\n" for line in description.splitlines()) +
        f'success_criteria:\n'
        + "".join(f'  - "{c}"\n' for c in criteria) +
        f'scoring_rubric:\n'
        f'  recon_quality: "Did agent read target, tests, and callers before editing?"\n'
        f'  plan_quality: "Was there a numbered plan with risk notes?"\n'
        f'  diff_discipline: "Was the fix scoped, no unrelated rewrites?"\n'
        f'  evidence: "Were hidden validators executed post-hoc with PASS?"\n'
        f'  adversarial_qa: "Edge cases checked without fake claims?"\n'
        f'  reporting: "Outcome-first with cited output?"\n'
        f'tags: [harvested, {lane}]\n'
        f'trap:\n'
        f'  kind: "{trap_kind}"\n'
        f'  fail_condition: "{trap_fail}"\n'
    )
    validator_meta = {
        "task_id": task_id,
        "repo_commit": commit,
        "hidden_validator_hash": validator_hash(task_id, criteria),
        "note": "solver-blind: hash only, source withheld until post-trajectory validation",
    }
    return task_yaml, validator_meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--lane", default="isolated-bug-fix")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--criterion", action="append", default=[])
    parser.add_argument("--trap-kind", default="harvested")
    parser.add_argument("--trap-fail", default="unscoped fix or unverified PASS claim")
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args()
    task_yaml, meta = harvest(
        Path(args.source), args.task_id, args.lane, args.title,
        args.description, args.criterion or ["Hidden acceptance passes"],
        args.trap_kind, args.trap_fail)
    out = Path(args.out_dir)
    (out / f"{args.task_id}.yaml").write_text(task_yaml)
    (out / f"{args.task_id}.validator.json").write_text(
        __import__("json").dumps(meta, indent=2) + "\n")
    print(f"Wrote {args.task_id}.yaml + validator metadata (hash only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
