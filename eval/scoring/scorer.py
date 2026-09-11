#!/usr/bin/env python3
"""
GRAVITAS Evaluation Scorer

Automated scoring for GRAVITAS evaluation metrics.
Parses agent logs, computes metrics, and outputs results.

Usage:
    python scorer.py --log-dir <path> --output <path>
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Data Classes ──────────────────────────────────────────────

@dataclass
class ToolCall:
    tool: str
    args: dict
    output: Optional[str] = None
    timestamp: Optional[str] = None
    is_mutation: bool = False


@dataclass
class CompletionClaim:
    claim: str
    timestamp: Optional[str] = None
    evidence: Optional[str] = None
    correct: Optional[bool] = None


@dataclass
class TaskRun:
    task_id: str
    condition: str
    run: int
    tool_calls: list = field(default_factory=list)
    completion_claims: list = field(default_factory=list)
    diff_files_changed: int = 0
    diff_lines_added: int = 0
    diff_lines_removed: int = 0
    plan_steps: int = 0
    adversarial_critique: bool = False
    verification_tools_run: list = field(default_factory=list)
    verification_all_passing: bool = False
    qa_prompts_run: int = 0
    qa_issues_found: int = 0
    qa_issues_fixed: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_total: int = 0
    report_structure: Optional[str] = None
    report_score: Optional[int] = None


# ── Mutation Detection ────────────────────────────────────────

MUTATING_TOOLS = {"write", "edit", "bash"}
READ_ONLY_TOOLS = {"read", "glob", "grep", "list_dir", "codebase_search"}

MUTATING_BASH_PATTERNS = [
    r"\brm\b",
    r"\bgit\s+push\b",
    r"\bgit\s+commit\b",
    r"\bgit\s+merge\b",
    r"\bgit\s+rebase\b",
    r"\bdocker\s+(run|deploy|push)\b",
    r"\bnpm\s+publish\b",
    r"\bpip\s+install\b",
]


def is_mutation(tool_call: ToolCall) -> bool:
    """Determine if a tool call is a mutation."""
    if tool_call.tool in MUTATING_TOOLS:
        if tool_call.tool == "bash":
            cmd = tool_call.args.get("command", "")
            for pattern in MUTATING_BASH_PATTERNS:
                if re.search(pattern, cmd):
                    return True
            return False
        return True
    if tool_call.tool in READ_ONLY_TOOLS:
        return False
    return False


def first_mutation_index(tool_calls: list) -> Optional[int]:
    """Find the index of the first mutation in tool calls."""
    for i, tc in enumerate(tool_calls):
        if is_mutation(tc):
            return i
    return None


# ── Repetition Detection ──────────────────────────────────────

def detect_repetitions(tool_calls: list) -> int:
    """Detect repeated tool+file+output patterns."""
    repetitions = 0
    seen = []
    for tc in tool_calls:
        key = (tc.tool, json.dumps(tc.args, sort_keys=True))
        if key in seen:
            repetitions += 1
        seen.append(key)
    return repetitions


# ── Metric Computation ────────────────────────────────────────

def compute_recon_rate(runs: list) -> float:
    """Compute recon-before-mutation rate."""
    non_trivial = [r for r in runs if len(r.tool_calls) > 3]
    if not non_trivial:
        return 0.0
    reads_first = 0
    for run in non_trivial:
        if run.tool_calls and not is_mutation(run.tool_calls[0]):
            reads_first += 1
    return reads_first / len(non_trivial)


def compute_diff_scoping_ratio(runs: list, reference_diffs: dict) -> float:
    """Compute average diff scoping ratio."""
    ratios = []
    for run in runs:
        if run.task_id in reference_diffs:
            ref = reference_diffs[run.task_id]
            actual = run.diff_lines_added + run.diff_lines_removed
            if ref > 0:
                ratios.append(actual / ref)
    return sum(ratios) / len(ratios) if ratios else 0.0


def compute_false_completion_rate(runs: list) -> float:
    """Compute false-completion rate."""
    total_claims = 0
    wrong_claims = 0
    for run in runs:
        for claim in run.completion_claims:
            total_claims += 1
            if claim.correct is False:
                wrong_claims += 1
    return wrong_claims / total_claims if total_claims > 0 else 0.0


def compute_failure_repetition_rate(runs: list) -> float:
    """Compute failure-repetition rate."""
    total_failures = 0
    repeated = 0
    for run in runs:
        # Count failures as tool calls that return errors
        failures = [tc for tc in run.tool_calls if tc.output and "error" in tc.output.lower()]
        total_failures += len(failures)
        repeated += detect_repetitions(run.tool_calls)
    return repeated / total_failures if total_failures > 0 else 0.0


def compute_token_overhead(baseline_runs: list, gravitas_runs: list) -> float:
    """Compute token overhead ratio."""
    baseline_tokens = sum(r.tokens_total for r in baseline_runs)
    gravitas_tokens = sum(r.tokens_total for r in gravitas_runs)
    if baseline_tokens == 0:
        return 0.0
    return gravitas_tokens / baseline_tokens


def compute_task_success_rate(runs: list) -> float:
    """Compute task success rate."""
    if not runs:
        return 0.0
    successful = sum(1 for r in runs if r.verification_all_passing)
    return successful / len(runs)


def compute_pushback_rate(runs: list, questionable_tasks: set) -> float:
    """Compute pushback rate."""
    questionable_runs = [r for r in runs if r.task_id in questionable_tasks]
    if not questionable_runs:
        return 0.0
    # This requires human review — placeholder
    return 0.0


# ── Report Generation ─────────────────────────────────────────

def generate_report(results: dict) -> str:
    """Generate a formatted evaluation report."""
    lines = [
        "# GRAVITAS Evaluation Results",
        "",
        "## Automated Metrics",
        "",
        "| Metric | Value | 95% CI | Interpretation |",
        "|--------|-------|--------|----------------|",
    ]

    for metric, data in results.items():
        value = data.get("value", 0)
        ci_low = data.get("ci_low", 0)
        ci_high = data.get("ci_high", 0)
        interpretation = data.get("interpretation", "")
        lines.append(f"| {metric} | {value:.3f} | [{ci_low:.3f}, {ci_high:.3f}] | {interpretation} |")

    lines.extend([
        "",
        "## Per-Pillar Breakdown",
        "",
        "| Pillar | Metric | Value |",
        "|--------|--------|-------|",
    ])

    pillar_metrics = {
        "1: Recon": "recon_before_mutation_rate",
        "4: Diff Scoping": "diff_scoping_ratio",
        "5: Evidence": "false_completion_rate",
        "8: Memory": "failure_repetition_rate",
        "Overall": "task_success_rate",
    }

    for pillar, metric in pillar_metrics.items():
        if metric in results:
            value = results[metric].get("value", 0)
            lines.append(f"| {pillar} | {metric} | {value:.3f} |")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────

def load_task_run(filepath: str) -> TaskRun:
    """Load a task run from a JSON file."""
    with open(filepath) as f:
        data = json.load(f)

    run = TaskRun(
        task_id=data["task_id"],
        condition=data["condition"],
        run=data["run"],
    )

    # Parse tool calls
    for tc in data.get("tool_calls", []):
        tool_call = ToolCall(
            tool=tc["tool"],
            args=tc.get("args", {}),
            output=tc.get("output"),
            timestamp=tc.get("timestamp"),
        )
        tool_call.is_mutation = is_mutation(tool_call)
        run.tool_calls.append(tool_call)

    # Parse completion claims
    for claim in data.get("completion_claims", []):
        run.completion_claims.append(CompletionClaim(
            claim=claim["claim"],
            timestamp=claim.get("timestamp"),
            evidence=claim.get("evidence"),
            correct=claim.get("correct"),
        ))

    # Parse diff
    diff = data.get("diff", {})
    run.diff_files_changed = diff.get("files_changed", 0)
    run.diff_lines_added = diff.get("lines_added", 0)
    run.diff_lines_removed = diff.get("lines_removed", 0)

    # Parse plan
    plan = data.get("plan", {})
    run.plan_steps = plan.get("steps", 0)
    run.adversarial_critique = plan.get("adversarial_critique", False)

    # Parse verification
    verification = data.get("verification", {})
    run.verification_tools_run = verification.get("tools_run", [])
    run.verification_all_passing = verification.get("all_passing", False)

    # Parse QA
    qa = data.get("qa", {})
    run.qa_prompts_run = qa.get("prompts_run", 0)
    run.qa_issues_found = qa.get("issues_found", 0)
    run.qa_issues_fixed = qa.get("issues_fixed", 0)

    # Parse tokens
    tokens = data.get("tokens", {})
    run.tokens_input = tokens.get("input", 0)
    run.tokens_output = tokens.get("output", 0)
    run.tokens_total = tokens.get("total", 0)

    # Parse report
    run.report_structure = data.get("report", {}).get("structure")
    run.report_score = data.get("report", {}).get("score")

    return run


def main():
    import argparse
    parser = argparse.ArgumentParser(description="GRAVITAS Evaluation Scorer")
    parser.add_argument("--log-dir", required=True, help="Directory containing task run logs")
    parser.add_argument("--output", required=True, help="Output file for results")
    parser.add_argument("--reference-diffs", help="JSON file with reference diff sizes")
    parser.add_argument("--questionable-tasks", help="JSON file with questionable task IDs")
    args = parser.parse_args()

    # Load task runs
    runs = []
    log_dir = Path(args.log_dir)
    for filepath in log_dir.glob("*.json"):
        try:
            run = load_task_run(str(filepath))
            runs.append(run)
        except Exception as e:
            print(f"Error loading {filepath}: {e}", file=sys.stderr)

    if not runs:
        print("No task runs found.", file=sys.stderr)
        sys.exit(1)

    # Load reference diffs
    reference_diffs = {}
    if args.reference_diffs:
        with open(args.reference_diffs) as f:
            reference_diffs = json.load(f)

    # Load questionable tasks
    questionable_tasks = set()
    if args.questionable_tasks:
        with open(args.questionable_tasks) as f:
            questionable_tasks = set(json.load(f))

    # Group runs by condition
    conditions = {}
    for run in runs:
        if run.condition not in conditions:
            conditions[run.condition] = []
        conditions[run.condition].append(run)

    # Compute metrics per condition
    results = {}
    for condition, cond_runs in conditions.items():
        results[condition] = {
            "recon_rate": compute_recon_rate(cond_runs),
            "diff_scoping": compute_diff_scoping_ratio(cond_runs, reference_diffs),
            "false_completion": compute_false_completion_rate(cond_runs),
            "failure_repetition": compute_failure_repetition_rate(cond_runs),
            "task_success": compute_task_success_rate(cond_runs),
            "pushback_rate": compute_pushback_rate(cond_runs, questionable_tasks),
        }

    # Compute overhead
    if "gemini_baseline" in conditions and "gemini_gravitas" in conditions:
        results["gemini_gravitas"]["token_overhead"] = compute_token_overhead(
            conditions["gemini_baseline"],
            conditions["gemini_gravitas"],
        )
    if "claude_baseline" in conditions and "claude_gravitas" in conditions:
        results["claude_gravitas"]["token_overhead"] = compute_token_overhead(
            conditions["claude_baseline"],
            conditions["claude_gravitas"],
        )

    # Generate report
    report = generate_report(results)

    # Write output
    with open(args.output, "w") as f:
        f.write(report)

    # Also write raw results as JSON
    json_output = args.output.replace(".md", ".json")
    with open(json_output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results written to {args.output} and {json_output}")


if __name__ == "__main__":
    main()
