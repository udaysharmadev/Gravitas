#!/usr/bin/env python3
"""Compatibility entry point for the v4 episode benchmark."""
import sys


print(
    "The v3 text-response scorer is retired. Validate repository-backed episodes with:\n"
    "  python benchmarks/runner/validate.py --episodes benchmarks/results\n"
    "  python benchmarks/runner/summarize.py --episodes benchmarks/results",
    file=sys.stderr,
)
raise SystemExit(2)
