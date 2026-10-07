#!/usr/bin/env python3
"""
GRAVITAS Benchmark Runner

Runs coding tasks through GRAVITAS protocol and measures quality metrics.
Compares Gemini output with/without GRAVITAS against Claude baseline.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Benchmark dimensions
DIMENSIONS = [
    "recon_quality",
    "plan_quality",
    "adversarial_catch",
    "verification_evidence",
    "anti_rationalization",
    "outcome_first",
]

# Scoring rubrics (0-5 scale)
RUBRICS = {
    "recon_quality": {
        0: "No recon — edited without reading",
        1: "Read target file only",
        2: "Read target + imports/exports",
        3: "Read target + related + config",
        4: "Read target + related + config + tests",
        5: "Read target + related + config + tests + git history",
    },
    "plan_quality": {
        0: "No plan — jumped to implementation",
        1: "Vague plan without specifics",
        2: "Plan with steps but no risk analysis",
        3: "Plan with steps + risk analysis",
        4: "Plan with steps + risk analysis + alternatives",
        5: "Plan with steps + risk + alternatives + confidence",
    },
    "adversarial_catch": {
        0: "No self-critique",
        1: "Mentioned issues without analysis",
        2: "Analyzed 1-2 issues",
        3: "Analyzed 3-4 issues with severity",
        4: "Analyzed 5+ issues with severity + mitigations",
        5: "Analyzed 5+ issues + mitigations + revised plan",
    },
    "verification_evidence": {
        0: "No verification",
        1: "Ran tests but didn't cite output",
        2: "Cited pass/fail counts",
        3: "Cited pass/fail counts + warnings",
        4: "Cited full output for key commands",
        5: "Full output + edge cases + regression check",
    },
    "anti_rationalization": {
        0: "Multiple anti-pattern violations",
        1: "One anti-pattern violation",
        2: "No violations but no active defense",
        3: "No violations + checked failure log",
        4: "No violations + failure log + pushed back",
        5: "No violations + failure log + pushed back + evidence",
    },
    "outcome_first": {
        0: "Started with preamble/greeting",
        1: "Started with process description",
        2: "Started with some context",
        3: "Started with partial answer",
        4: "Started with clear answer",
        5: "Started with answer + evidence",
    },
}


def load_task(task_path: str) -> dict[str, Any]:
    """Load a benchmark task from YAML/JSON."""
    with open(task_path) as f:
        if task_path.endswith(".json"):
            return json.load(f)
        # Simple YAML-like parsing for .md files
        content = f.read()
        return {"content": content, "path": task_path}


def score_response(response: str, tool_calls: list[dict]) -> dict[str, int]:
    """Score a GRAVITAS response against rubrics."""
    scores = {}

    # Recon quality — check if read was called before edit/write
    reads = [t for t in tool_calls if t.get("tool") == "read"]
    edits = [t for t in tool_calls if t.get("tool") in ("edit", "write")]
    if len(reads) > len(edits) * 2:
        scores["recon_quality"] = 5
    elif len(reads) > len(edits):
        scores["recon_quality"] = 4
    elif reads:
        scores["recon_quality"] = 3
    else:
        scores["recon_quality"] = 0

    # Plan quality — check for plan structure
    has_plan = "## Plan" in response or "## Implementation" in response
    has_risk = "risk" in response.lower() or "mitigation" in response.lower()
    has_alternative = "alternative" in response.lower() or "option" in response.lower()
    if has_plan and has_risk and has_alternative:
        scores["plan_quality"] = 5
    elif has_plan and has_risk:
        scores["plan_quality"] = 4
    elif has_plan:
        scores["plan_quality"] = 3
    else:
        scores["plan_quality"] = 0

    # Verification evidence
    has_test_output = "pass" in response.lower() or "fail" in response.lower()
    has_counts = "passed" in response.lower() or "/47" in response or "/52" in response
    has_warnings = "warning" in response.lower()
    if has_test_output and has_counts and has_warnings:
        scores["verification_evidence"] = 5
    elif has_test_output and has_counts:
        scores["verification_evidence"] = 4
    elif has_test_output:
        scores["verification_evidence"] = 3
    else:
        scores["verification_evidence"] = 0

    # Anti-rationalization
    anti_patterns = [
        "this should work",
        "i think",
        "probably",
        "genuinely",
        "honestly",
        "straightforwardly",
    ]
    violations = sum(1 for p in anti_patterns if p in response.lower())
    scores["anti_rationalization"] = max(0, 5 - violations)

    # Outcome-first
    first_sentence = response.split(".")[0] if response else ""
    has_preamble = any(
        p in first_sentence.lower()
        for p in ["great", "happy to", "sure", "let me", "i'll"]
    )
    scores["outcome_first"] = 0 if has_preamble else 5

    # Adversarial catch
    has_critique = "## Critique" in response or "## Issues" in response
    has_severity = "high" in response.lower() or "critical" in response.lower()
    if has_critique and has_severity:
        scores["adversarial_catch"] = 4
    elif has_critique:
        scores["adversarial_catch"] = 3
    else:
        scores["adversarial_catch"] = 0

    return scores


def calculate_overall(scores: dict[str, int]) -> float:
    """Calculate overall score from dimension scores."""
    if not scores:
        return 0.0
    return sum(scores.values()) / len(scores)


def run_benchmark(task_path: str, model: str = "gemini-2.5-pro") -> dict:
    """Run a single benchmark task."""
    task = load_task(task_path)
    start_time = datetime.now()

    # This would be replaced with actual API calls
    result = {
        "task": task_path,
        "model": model,
        "timestamp": start_time.isoformat(),
        "scores": {},
        "overall": 0.0,
        "notes": "Run manually or integrate with API",
    }

    return result


def generate_report(results: list[dict]) -> str:
    """Generate a benchmark report."""
    report = []
    report.append("# GRAVITAS Benchmark Report")
    report.append(f"\nGenerated: {datetime.now().isoformat()}")
    report.append(f"\nTasks evaluated: {len(results)}")

    # Average scores
    all_scores = {dim: [] for dim in DIMENSIONS}
    for result in results:
        for dim, score in result.get("scores", {}).items():
            all_scores[dim].append(score)

    report.append("\n## Average Scores by Dimension\n")
    report.append("| Dimension | Average | Target | Status |")
    report.append("|-----------|---------|--------|--------|")

    for dim in DIMENSIONS:
        scores = all_scores[dim]
        avg = sum(scores) / len(scores) if scores else 0
        target = 4.0
        status = "✅" if avg >= target else "❌"
        report.append(f"| {dim} | {avg:.1f} | {target} | {status} |")

    # Overall
    all_overalls = [r.get("overall", 0) for r in results]
    overall_avg = sum(all_overalls) / len(all_overalls) if all_overalls else 0
    report.append(f"\n**Overall Average: {overall_avg:.1f} / 5.0**")

    return "\n".join(report)


def main():
    """Main benchmark runner."""
    corpus_dir = Path("benchmarks/corpus")
    results_dir = Path("benchmarks/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    # Find all tasks
    tasks = list(corpus_dir.glob("*.md")) + list(corpus_dir.glob("*.json"))

    if not tasks:
        print("No tasks found in benchmarks/corpus/")
        print("Add task files (YAML/JSON/Markdown) to get started.")
        return

    print(f"Found {len(tasks)} tasks")

    results = []
    for task_path in tasks:
        print(f"\nRunning: {task_path.name}")
        result = run_benchmark(str(task_path))
        results.append(result)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"results_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    # Generate report
    report = generate_report(results)
    report_file = results_dir / f"report_{timestamp}.md"
    with open(report_file, "w") as f:
        f.write(report)

    print(f"\nResults saved to: {results_file}")
    print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    main()
