#!/usr/bin/env python3
"""
GRAVITAS Metrics Collector

Analyzes code quality metrics for GRAVITAS-evaluated outputs.
"""

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


def count_functions(code: str) -> int:
    """Count function definitions in code."""
    try:
        tree = ast.parse(code)
        return sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
    except SyntaxError:
        return 0


def count_classes(code: str) -> int:
    """Count class definitions in code."""
    try:
        tree = ast.parse(code)
        return sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    except SyntaxError:
        return 0


def count_comments(code: str) -> int:
    """Count comment lines."""
    return sum(1 for line in code.split("\n") if line.strip().startswith("#"))


def count_type_hints(code: str) -> int:
    """Count lines with type hints."""
    return len(re.findall(r":\s*(str|int|float|bool|list|dict|None|Any)", code))


def measure_complexity(code: str) -> dict[str, Any]:
    """Measure code complexity metrics."""
    lines = code.split("\n")
    non_empty = [l for l in lines if l.strip()]

    return {
        "total_lines": len(lines),
        "non_empty_lines": len(non_empty),
        "functions": count_functions(code),
        "classes": count_classes(code),
        "comments": count_comments(code),
        "type_hints": count_type_hints(code),
        "avg_line_length": sum(len(l) for l in non_empty) / max(len(non_empty), 1),
    }


def analyze_file(file_path: str) -> dict[str, Any]:
    """Analyze a single file."""
    with open(file_path) as f:
        code = f.read()

    metrics = measure_complexity(code)
    metrics["file"] = file_path
    metrics["language"] = Path(file_path).suffix.lstrip(".")

    return metrics


def analyze_directory(dir_path: str) -> list[dict[str, Any]]:
    """Analyze all code files in a directory."""
    results = []
    path = Path(dir_path)

    for ext in ["*.py", "*.ts", "*.js", "*.rs", "*.go", "*.java"]:
        for file_path in path.rglob(ext):
            # Skip node_modules, __pycache__, etc.
            if any(skip in str(file_path) for skip in ["node_modules", "__pycache__", ".git", "dist"]):
                continue
            results.append(analyze_file(str(file_path)))

    return results


def generate_report(metrics: list[dict[str, Any]]) -> str:
    """Generate a metrics report."""
    report = []
    report.append("# GRAVITAS Code Metrics Report\n")

    if not metrics:
        report.append("No files analyzed.")
        return "\n".join(report)

    # Summary
    total_lines = sum(m["total_lines"] for m in metrics)
    total_functions = sum(m["functions"] for m in metrics)
    total_classes = sum(m["classes"] for m in metrics)
    total_comments = sum(m["comments"] for m in metrics)
    total_type_hints = sum(m["type_hints"] for m in metrics)

    report.append("## Summary\n")
    report.append(f"- Files analyzed: {len(metrics)}")
    report.append(f"- Total lines: {total_lines:,}")
    report.append(f"- Functions: {total_functions}")
    report.append(f"- Classes: {total_classes}")
    report.append(f"- Comments: {total_comments}")
    report.append(f"- Type hints: {total_type_hints}")

    # By language
    by_language = {}
    for m in metrics:
        lang = m["language"]
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(m)

    report.append("\n## By Language\n")
    report.append("| Language | Files | Lines | Functions | Classes |")
    report.append("|----------|-------|-------|-----------|---------|")

    for lang, lang_metrics in sorted(by_language.items()):
        files = len(lang_metrics)
        lines = sum(m["total_lines"] for m in lang_metrics)
        funcs = sum(m["functions"] for m in lang_metrics)
        classes = sum(m["classes"] for m in lang_metrics)
        report.append(f"| {lang} | {files} | {lines:,} | {funcs} | {classes} |")

    # Quality indicators
    report.append("\n## Quality Indicators\n")

    avg_comments_per_file = total_comments / max(len(metrics), 1)
    avg_type_hints_per_file = total_type_hints / max(len(metrics), 1)

    report.append(f"- Avg comments per file: {avg_comments_per_file:.1f}")
    report.append(f"- Avg type hints per file: {avg_type_hints_per_file:.1f}")

    if avg_comments_per_file > 2:
        report.append("- ✅ Good documentation coverage")
    else:
        report.append("- ⚠️ Low documentation coverage")

    if avg_type_hints_per_file > 3:
        report.append("- ✅ Good type safety")
    else:
        report.append("- ⚠️ Low type hint usage")

    return "\n".join(report)


def main():
    """Main metrics collector."""
    if len(sys.argv) < 2:
        print("Usage: python metrics.py <directory>")
        sys.exit(1)

    dir_path = sys.argv[1]
    metrics = analyze_directory(dir_path)

    report = generate_report(metrics)
    print(report)

    # Save to file
    output_file = Path("benchmarks/results/metrics_report.md")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write(report)

    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()
