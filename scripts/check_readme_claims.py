#!/usr/bin/env python3
"""Fail CI if the public README drifts into unsupported benchmark claims."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")

required = [
    "Research preview: comparative performance is not yet measured.",
    "GRAVITAS changes the engineering process, not model weights.",
    "30 registered task specifications across 10 planned lanes",
]
for phrase in required:
    if phrase not in README:
        raise SystemExit(f"README is missing required evidence disclosure: {phrase}")

prohibited = [
    "gap closure",
    "Functional Solve Rate",
    "false completion rate",
    "99% Claude",
    "Claude replacement",
    "better than Claude",
]
lower = README.lower()
for phrase in prohibited:
    if phrase.lower() in lower:
        raise SystemExit(f"README contains unsupported public claim: {phrase}")

print("PASS public README claims are research-preview safe")
