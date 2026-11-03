#!/usr/bin/env python3
"""Claim generation pipeline: validated episodes -> markdown + CSV.

The pipeline is claim-gated. Reports require explicit repository provenance,
matched revisions, and at least 30 distinct tasks with 5 valid paired runs each.
Reports that do not meet the gate retain a research-preview banner and explain
the blockers. Infrastructure failures remain visible as INVALID counts.
"""
import csv
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from compare import MIN_PUBLICATION_TASKS, MIN_RUNS_PER_TASK
except ImportError:  # pragma: no cover - package import
    from benchmarks.runner.compare import MIN_PUBLICATION_TASKS, MIN_RUNS_PER_TASK


DISCLOSURES = [
    "Infrastructure failures are classified INVALID and excluded from denominators; they are never counted as model failures.",
    "Synthetic fixture corpora prove benchmark plumbing; they are not licensed OSS tasks and do not generalize.",
    "Publication requires at least 30 distinct tasks with 5 valid paired runs per task, explicit repository provenance, and matched model/task/evaluator revisions.",
    "Provenance checks validate declarations and pairing, not artifact authenticity; independent review of raw evidence is still required.",
    "All rates carry Wilson 95% confidence intervals; continuous metrics report median and p90.",
]


def publication_ready(comparisons):
    """Require the complete eligibility result, not a legacy boolean claim."""
    if not comparisons:
        return False
    return all(
        isinstance(comparison, dict)
        and comparison.get("publication_ready") is True
        and comparison.get("publication_blockers") == []
        and all(type(comparison.get(field)) is int for field in
                ("paired_episodes", "paired_tasks", "min_pairs_per_task"))
        and comparison["paired_tasks"] >= MIN_PUBLICATION_TASKS
        and comparison["min_pairs_per_task"] >= MIN_RUNS_PER_TASK
        and comparison["paired_episodes"] >= comparison["paired_tasks"] * comparison["min_pairs_per_task"]
        for comparison in comparisons
    )


def render_markdown(summary, comparisons, meta=None, publish=False):
    """Render the results report.  Raises ValueError when publish=True but the gate fails."""
    meta = meta or {}
    compared = {comparison.get(field) for comparison in comparisons
                for field in ("baseline", "treatment")}
    uncompared = sorted(set(summary) - compared)
    ready = publication_ready(comparisons) and not uncompared
    if publish and not ready:
        raise ValueError(
            "publication gate failed: every comparison needs repository provenance, matched revisions, "
            "and at least 30 distinct tasks with 5 valid paired runs each; all reported configurations "
            "must be covered. Regenerate without --publish to inspect publication blockers"
        )

    lines = ["# GravitasBench Results", ""]
    if not ready:
        lines += [
            "> **RESEARCH PREVIEW — NOT PUBLICATION-READY.** This report documents runner ",
            "> plumbing only. It must not be cited as a model comparison.",
            "",
        ]
    lines += ["## Disclosure", ""]
    lines += [f"- {item}" for item in DISCLOSURES]
    lines += [
        "",
        "## Run metadata",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Dataset: {meta.get('dataset', 'unspecified')}",
        f"- Models and effort: {meta.get('models', 'unspecified')}",
        f"- Antigravity version: {meta.get('antigravity_version', 'unspecified')}",
        f"- Gravitas version: {meta.get('gravitas_version', 'unspecified')}",
        f"- Raw trajectories: {meta.get('raw_trajectories', 'unspecified')}",
        f"- Reproduce: {meta.get('reproduce', 'unspecified')}",
        "",
        "## Per-configuration metrics",
        "",
    ]
    lines += _metric_table(summary)
    lines += ["", "## Paired comparisons", ""]
    if comparisons:
        lines += _comparison_table(comparisons)
    else:
        lines += ["_No paired comparison was requested._"]
    if not ready:
        lines += ["", "## Publication blockers", ""]
        if not comparisons:
            lines += ["- No paired comparison was requested."]
        if uncompared:
            lines += ["- Configurations without a checked comparison: " + ", ".join(uncompared)]
        for comparison in comparisons:
            label = f"{comparison.get('baseline', 'baseline')} vs {comparison.get('treatment', 'treatment')}"
            blockers = comparison.get("publication_blockers") or ["complete publication eligibility evidence is unavailable"]
            if not publication_ready([comparison]):
                lines += [f"- {label}: {reason}" for reason in blockers]
    lines += ["", "## INVALID episodes", ""]
    invalid_total = meta.get("invalid_episodes")
    lines += [f"- {invalid_total} episode(s) recorded as infrastructure failures." if invalid_total is not None
              else "- This report was generated from the per-configuration summary; run "
                   "`benchmarks/runner/validate.py` over raw episodes for the INVALID count."]
    return "\n".join(lines) + "\n"


def _metric_table(summary):
    header = "| Configuration | runs | FSR | RC | RR | SVR | PVR | IRR | FCR | EI | SQE | median tokens | p90 tokens |"
    divider = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    rows = [header, divider]
    for config, metrics in summary.items():
        def cell(rate):
            if rate is None:
                return "n/a"
            if isinstance(rate, dict):
                if rate.get("rate") is None:
                    return f"n/a (n={rate['n']})"
                low, high = rate["ci95"]
                return f"{rate['rate']:.4f} [{low:.4f}, {high:.4f}]"
            return str(rate)
        rows.append(
            f"| {config} | {metrics['runs']} | {cell(metrics['fsr'])} | {cell(metrics['rc'])} "
            f"| {cell(metrics['rr'])} | {cell(metrics['svr'])} | {cell(metrics['pvr'])} "
            f"| {cell(metrics['irr'])} | {cell(metrics['fcr'])} | {cell(metrics['ei'])} "
            f"| {metrics['sqe'] if metrics['sqe'] is not None else 'n/a'} "
            f"| {metrics['median_tokens'] if metrics['median_tokens'] is not None else 'n/a'} "
            f"| {metrics['p90_tokens'] if metrics['p90_tokens'] is not None else 'n/a'} |"
        )
    return rows


def _comparison_table(comparisons):
    header = "| Baseline | Treatment | paired n | baseline FSR | treatment FSR | delta | bootstrap CI95 | McNemar p | publication-ready |"
    divider = "|---|---|---:|---:|---:|---:|---:|---:|:---:|"
    rows = [header, divider]
    for comparison in comparisons:
        ci = comparison.get("fsr_delta_bootstrap_ci95")
        ci_text = f"[{ci[0]:.4f}, {ci[1]:.4f}]" if ci else "n/a"
        rows.append(
            f"| {comparison['baseline']} | {comparison['treatment']} | {comparison['paired_episodes']} "
            f"| {comparison['baseline_fsr'] if comparison['baseline_fsr'] is not None else 'n/a'} "
            f"| {comparison['treatment_fsr'] if comparison['treatment_fsr'] is not None else 'n/a'} "
            f"| {comparison['fsr_delta'] if comparison['fsr_delta'] is not None else 'n/a'} "
            f"| {ci_text} | {comparison['mcnemar']['two_sided_exact_p']} "
            f"| {'yes' if publication_ready([comparison]) else 'NO'} |"
        )
    return rows


def write_summary_csv(summary, path):
    """Write one row per configuration of primary metrics; returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "configuration", "runs", "fsr", "fsr_ci95_low", "fsr_ci95_high", "rc", "rr", "svr",
        "pvr", "irr", "fcr", "ei", "sqe", "median_tokens", "p90_tokens",
        "median_duration_seconds", "p90_duration_seconds",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for config, metrics in summary.items():
            fsr = metrics["fsr"]
            writer.writerow({
                "configuration": config,
                "runs": metrics["runs"],
                "fsr": fsr["rate"] if fsr["rate"] is not None else "",
                "fsr_ci95_low": fsr["ci95"][0] if fsr["ci95"] else "",
                "fsr_ci95_high": fsr["ci95"][1] if fsr["ci95"] else "",
                "rc": metrics["rc"] if metrics["rc"] is not None else "",
                "rr": metrics["rr"]["rate"] if metrics["rr"]["rate"] is not None else "",
                "svr": metrics["svr"]["rate"] if metrics["svr"]["rate"] is not None else "",
                "pvr": metrics["pvr"]["rate"] if metrics["pvr"]["rate"] is not None else "",
                "irr": metrics["irr"]["rate"] if metrics["irr"]["rate"] is not None else "",
                "fcr": metrics["fcr"]["rate"] if metrics["fcr"]["rate"] is not None else "",
                "ei": metrics["ei"]["rate"] if metrics["ei"]["rate"] is not None else "",
                "sqe": metrics["sqe"] if metrics["sqe"] is not None else "",
                "median_tokens": metrics["median_tokens"] if metrics["median_tokens"] is not None else "",
                "p90_tokens": metrics["p90_tokens"] if metrics["p90_tokens"] is not None else "",
                "median_duration_seconds": metrics["median_duration_seconds"] if metrics["median_duration_seconds"] is not None else "",
                "p90_duration_seconds": metrics["p90_duration_seconds"] if metrics["p90_duration_seconds"] is not None else "",
            })
    return path


def scrub_episode(episode):
    """Return a publication-safe copy without hidden-validator output text."""
    scrubbed = copy.deepcopy(episode)
    for validator in scrubbed.get("validator_outputs", []):
        if not isinstance(validator, dict) or "output" not in validator:
            continue
        output = validator.pop("output")
        if isinstance(output, str):
            validator["output_sha256"] = hashlib.sha256(output.encode("utf-8")).hexdigest()
        validator["output_redacted"] = True
    return scrubbed


def write_report(summary, comparisons, output_dir, meta=None, publish=False, episodes=None):
    """Write report artifacts and sanitized episode exports into output_dir."""
    if episodes is not None:
        episodes = list(episodes)
    if episodes is not None and (publish or comparisons):
        try:
            from compare import compare
            from metrics import aggregate
            from validate import episode_errors
        except ImportError:  # pragma: no cover - package import
            from benchmarks.runner.compare import compare
            from benchmarks.runner.metrics import aggregate
            from benchmarks.runner.validate import episode_errors
        for episode in episodes:
            errors = episode_errors(episode, {})
            if errors:
                raise ValueError("episode validation failed: " + "; ".join(errors))
        summary = aggregate(episodes)
        comparisons = [compare(episodes, comparison["baseline"], comparison["treatment"])
                       for comparison in comparisons]
        meta = {**(meta or {}), "invalid_episodes": sum(
            episode.get("infrastructure_failure") is True for episode in episodes
        )}
    elif publish:
        raise ValueError("publication gate failed: raw episodes are required to verify report eligibility")
    markdown = render_markdown(summary, comparisons, meta=meta, publish=publish)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.md"
    report_path.write_text(markdown)
    csv_path = write_summary_csv(summary, output_dir / "summary.csv")
    if episodes is not None:
        export_path = output_dir / "episodes.jsonl"
        export_path.write_text("".join(
            json.dumps(scrub_episode(episode), sort_keys=True) + "\n"
            for episode in episodes
        ), encoding="utf-8")
    return report_path, csv_path
