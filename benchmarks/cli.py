#!/usr/bin/env python3
"""GravitasBench reproducibility CLI (invoked via `gravitas bench ...`)."""
import argparse
import json
import shutil
import sys
from pathlib import Path

RUNNER = Path(__file__).resolve().parent / "runner"
sys.path.insert(0, str(RUNNER))


def cmd_doctor(_args):
    """ readiness: agy present, manifest parses, task specs exist. """
    from run import ROOT, load_manifest
    errors = []
    if not shutil.which("agy"):
        errors.append("agy not found on PATH (Antigravity CLI required for model episodes)")
    try:
        manifest = load_manifest()
        lanes = manifest.get("lanes", {})
        task_ids = [t for lane in lanes.values() for t in lane.get("tasks", [])]
        specs = {p.stem for p in (ROOT / "eval" / "tasks").glob("*.yaml")}
        missing = sorted(set(task_ids) - specs)
        if missing:
            errors.append(f"missing task specs: {missing}")
        print(f"lanes=10 tasks={len(task_ids)} specs_present={len(specs)}")
    except Exception as error:  # noqa: BLE001 -- doctor must report, not crash
        errors.append(f"manifest unreadable: {error}")
    holdout = (manifest.get("holdout") or {}).get("tasks", []) if "manifest" in dir() else []
    print(f"holdout_tasks={holdout}")
    for error in errors:
        print(f"BLOCKED {error}")
    print("Benchmark readiness: " + ("PASS" if not errors else "BLOCKED"))
    return 0 if not errors else 1


def cmd_build_corpus(args):
    """Materialize disposable synthetic fixtures for every manifest task."""
    from fixtures import materialize
    from run import load_manifest
    manifest = load_manifest()
    out = Path(args.out)
    task_ids = [t for lane in manifest["lanes"].values() for t in lane.get("tasks", [])]
    built = 0
    for task_id in task_ids:
        materialize(task_id, out / task_id)
        built += 1
    print(json.dumps({"built": built, "out": str(out)}))
    return 0


def cmd_run(args):
    """Run one implementation episode (needs GEMINI_API_KEY or Keychain entry)."""
    from implementation import check_holdout, run_episode
    from run import load_manifest, load_task, result_path
    task = load_task(args.task_file)
    holdout_error = check_holdout(task["task_id"], load_manifest(), args.include_holdout)
    if holdout_error:
        print(f"ERROR {holdout_error}")
        return 3
    episode = run_episode(task, args.model, args.configuration, args.max_steps)
    output = result_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(episode, indent=2) + "\n")
    print(f"Wrote {output} solve={episode['functional_solve']} invalid={episode['infrastructure_failure']}")
    return 0 if not episode["infrastructure_failure"] else 2


def cmd_report(args):
    """Validate episodes, aggregate, compare, and write the gated report."""
    from compare import compare
    from metrics import aggregate
    from report import write_report
    from validate import validate_episodes
    episodes_dir = Path(args.episodes)
    episodes, invalid = validate_episodes(episodes_dir)
    summary = aggregate(episodes)
    comparisons = []
    if args.baseline and args.treatment:
        comparisons = [compare(episodes, args.baseline, args.treatment)]
    out = Path(args.out)
    meta = {"dataset": str(episodes_dir), "invalid_episodes": invalid,
            "models": f"{args.baseline} vs {args.treatment}"}
    report_path, csv_path = write_report(summary, comparisons, out, meta=meta,
                                         publish=args.publish)
    print(f"Wrote {report_path} and {csv_path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="GravitasBench reproducibility CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    build_corpus = sub.add_parser("build-corpus")
    build_corpus.add_argument("--out", required=True)
    run = sub.add_parser("run")
    run.add_argument("--task-file", required=True)
    run.add_argument("--model", default="gemini-3.8-flash")
    run.add_argument("--configuration", default="gemini-synthetic")
    run.add_argument("--max-steps", type=int, default=12)
    run.add_argument("--include-holdout", action="store_true")
    run.add_argument("--output", required=True)
    report = sub.add_parser("report")
    report.add_argument("--episodes", required=True)
    report.add_argument("--out", required=True)
    report.add_argument("--baseline", default="")
    report.add_argument("--treatment", default="")
    report.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return cmd_doctor(args)
    if args.command == "build-corpus":
        return cmd_build_corpus(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "report":
        return cmd_report(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
