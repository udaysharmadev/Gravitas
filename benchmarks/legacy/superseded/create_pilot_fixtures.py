import os
import json
from pathlib import Path
import subprocess
import shutil

fixtures_dir = Path("benchmarks/fixtures")
tasks_dir = Path("eval/tasks")
fixtures_dir.mkdir(parents=True, exist_ok=True)
tasks_dir.mkdir(parents=True, exist_ok=True)

lanes = [
    ("L1", "isolated-bug-fix", "Fix simple addition bug"),
    ("L2", "multi-file-feature", "Add multiply feature across files"),
    ("L3", "debugging-root-cause", "Find why division by zero isn't handled"),
    ("L4", "regression-sensitive-refactor", "Refactor calc without breaking addition"),
    ("L5", "security-sensitive", "Prevent command injection in calc eval"),
    ("L6", "ambiguous-requirements", "Make calc support 'more numbers'"),
    ("L7", "plan-only-constraint", "Plan how to add trig functions"),
    ("L8", "interrupted-resumed", "Finish adding history feature"),
    ("L9", "tool-failure-adversarial", "Use calculator with a broken dependency"),
    ("L10", "long-horizon", "Migrate entire calc to OOP"),
]

def make_repo(lane_id, name):
    d = fixtures_dir / lane_id
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=d, capture_output=True)
    
    calc_content = "def add(a, b): return a + b\n"
    if lane_id == "L1":
        calc_content = "def add(a, b): return a - b\n"
    (d / "calc.py").write_text(calc_content)
    (d / "test_calc.py").write_text("from calc import add\nassert add(1, 1) == 2\n")
    
    subprocess.run(["git", "add", "."], cwd=d, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=d, capture_output=True)
    
    bundle_path = fixtures_dir / f"{lane_id}.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle_path.resolve()), "HEAD"], cwd=d, capture_output=True)
    return bundle_path

for idx, (l_id, l_name, l_title) in enumerate(lanes):
    bundle = make_repo(l_id, l_title)
    
    yml = f"""task_id: PILOT-{l_id}
stratum: CONTROLLED
lane: {l_name}
title: "{l_title}"
repository_url: "file://{bundle.absolute()}"
starting_commit: HEAD
task_provenance: Controlled synthetic fixture for pilot
task_selection_rationale: Validates {l_name}
description: >
  This is a controlled task for {l_name}. 
  Fix the codebase so that test_calc.py passes.
success_criteria:
  - id: AC-001
    statement: Tests pass
    validators: [VAL-001]
validators:
  - id: VAL-001
    command: python3 test_calc.py
    required: true
timeout: 60
"""
    if l_id == "L7":
        yml += """  - id: VAL-002
    command: git diff --quiet && git diff --staged --quiet
    required: true
"""
    (tasks_dir / f"{l_id}-PILOT.yaml").write_text(yml)

print("Created 10 pilot fixtures and task definitions.")
