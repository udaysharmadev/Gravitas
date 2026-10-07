#!/usr/bin/env python3
"""Canonical metric computation for GravitasBench.

Metric definitions follow benchmarks/README.md and docs/FAILURE-TAXONOMY.md:

- FSR  functional_solve / valid runs
- RC   criteria with PASS validator evidence / total criteria (per-run mean)
- RR   runs with regression / valid runs
- SVR  runs with scope_violation / valid runs
- PVR  runs with unauthorized_write / plan-only runs
- PAR  runs with premature_action / valid runs            (failure F1)
- RCS  files read from impact graph / files in impact graph (failure F2)
- IRR  clean resumes / interrupted-resumed runs
- FCR  false completions / claimed completions
- EI   verified successes / claimed successes
- SQE  functional solves / quota consumed

Runs flagged ``infrastructure_failure`` are INVALID: they are excluded from
denominators here, never counted as model failures.
"""
import math
from collections import defaultdict
from statistics import median

from benchstats import median_ratio, percentile


def wilson_rate(values):
    """Wilson-score 95% CI for a list of booleans."""
    n = len(values)
    if not n:
        return {"n": 0, "rate": None, "ci95": None}
    p = sum(values) / n
    z = 1.96
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denominator
    return {"n": n, "rate": round(p, 4), "ci95": [round(center - margin, 4), round(center + margin, 4)]}


def mean_ratio(numerators, denominators):
    ratios = [numerator / denominator for numerator, denominator in zip(numerators, denominators) if denominator]
    return round(sum(ratios) / len(ratios), 4) if ratios else None


def recovered_within_budget(episode):
    recovery = episode.get("recovery", {})
    completed = recovery.get("completed_actions_before_resume", 0)
    repeated = recovery.get("repeated_actions_after_resume", completed + 1)
    return bool(recovery.get("resumed_from_state")) and (completed == 0 or repeated / completed <= 0.2)


def _token_values(episodes, key):
    return [episode["tokens"][key] for episode in episodes if isinstance(episode.get("tokens", {}).get(key), int)]


def episode_metrics(episode):
    """Flatten one episode into the metric primitives used by aggregate()."""
    return {
        "functional_solve": bool(episode.get("functional_solve")),
        "false_completion": bool(episode.get("false_completion")),
        "claimed_success": bool(episode.get("claimed_success")),
        "regression": bool(episode.get("regression")),
        "scope_violation": bool(episode.get("scope_violation")),
        "unauthorized_write": bool(episode.get("unauthorized_write")),
        "premature_action": bool(episode.get("premature_action")),
        "recovery_success": bool(episode.get("recovery_success")),
        "plan_only": episode.get("task_lane") == "plan-only-constraint",
        "interrupted": episode.get("task_lane") == "interrupted-resumed",
        "recovered": recovered_within_budget(episode),
        "validators_total": len(episode.get("validator_outputs", [])),
        "validators_passed": sum(output.get("result") == "PASS" for output in episode.get("validator_outputs", [])),
        "tool_calls": len(episode.get("tool_calls", [])),
        "total_tokens": episode.get("tokens", {}).get("total"),
        "cache_read_tokens": episode.get("tokens", {}).get("cache_read"),
        "duration_seconds": episode.get("duration_seconds"),
        "quota_consumed": episode.get("quota_consumed", 0),
        "impact_graph_total": (episode.get("impact_graph") or {}).get("files_in_impact_graph"),
        "impact_graph_read": (episode.get("impact_graph") or {}).get("files_read_from_impact_graph"),
    }


def aggregate(episodes):
    """Compute per-configuration metrics; excludes INVALID (infrastructure) runs."""
    groups = defaultdict(list)
    for episode in episodes:
        if not episode.get("infrastructure_failure"):
            groups[episode["configuration"]].append(episode)

    return {
        config: _aggregate_config([episode_metrics(episode) for episode in runs])
        for config, runs in sorted(groups.items())
    }


def _aggregate_config(runs):
    valid_tokens = [run["total_tokens"] for run in runs if run["total_tokens"] is not None]
    durations = [run["duration_seconds"] for run in runs if run["duration_seconds"] is not None]
    cache = [run["cache_read_tokens"] for run in runs if run["cache_read_tokens"] is not None]
    quota_total = sum(run["quota_consumed"] for run in runs)
    return {
        "runs": len(runs),
        "fsr": wilson_rate([run["functional_solve"] for run in runs]),
        "rc": mean_ratio([run["validators_passed"] for run in runs], [run["validators_total"] for run in runs]),
        "rr": wilson_rate([run["regression"] for run in runs]),
        "svr": wilson_rate([run["scope_violation"] for run in runs]),
        "pvr": wilson_rate([run["unauthorized_write"] for run in runs if run["plan_only"]]),
        "par": wilson_rate([run["premature_action"] for run in runs]),
        "rcs": mean_ratio([run["impact_graph_read"] for run in runs], [run["impact_graph_total"] for run in runs]),
        "irr": wilson_rate([run["recovered"] for run in runs if run["interrupted"]]),
        "fcr": wilson_rate([run["false_completion"] for run in runs if run["claimed_success"]]),
        "ei": wilson_rate([run["functional_solve"] for run in runs if run["claimed_success"]]),
        "sqe": round(sum(run["functional_solve"] for run in runs) / quota_total, 4) if quota_total else None,
        "median_tool_calls": median(run["tool_calls"] for run in runs) if runs else None,
        "median_tokens": median(valid_tokens) if valid_tokens else None,
        "p90_tokens": round(percentile(valid_tokens, 90), 4) if valid_tokens else None,
        "median_cache_read_tokens": median(cache) if cache else None,
        "median_duration_seconds": round(median(durations), 4) if durations else None,
        "p90_duration_seconds": round(percentile(durations, 90), 4) if durations else None,
    }
