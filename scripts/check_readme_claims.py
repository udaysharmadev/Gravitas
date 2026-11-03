#!/usr/bin/env python3
"""Fail CI if the public README drifts into unsupported benchmark claims."""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
manifest = yaml.safe_load((ROOT / "benchmarks" / "manifest.yaml").read_text(encoding="utf-8"))
lanes = manifest["lanes"]
task_ids = [task_id for lane in lanes.values() for task_id in lane.get("tasks", [])]
if len(set(task_ids)) != len(task_ids) or manifest["meta"]["task_count"] != len(task_ids):
    raise SystemExit("benchmark registry task count is inconsistent")

required = [
    "Research preview: comparative performance is not yet measured.",
    "GRAVITAS changes the engineering process, not model weights.",
    f"{len(task_ids)} registered task specifications across {len(lanes)} planned lanes",
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
    "Claude-like",
    "like Claude",
    "forces Gemini",
    "competitive with Claude",
]
lower = README.lower()
for phrase in prohibited:
    if phrase.lower() in lower:
        raise SystemExit(f"README contains unsupported public claim: {phrase}")

print("PASS public README claims are research-preview safe")
