#!/usr/bin/env python3
"""Validate GravitasBench schemas, task registry, and trigger-eval dataset."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def audit():
    import yaml
    from jsonschema import Draft7Validator

    errors = []
    for schema_path in sorted((ROOT / "schemas").glob("*.json")):
        try:
            Draft7Validator.check_schema(json.loads(schema_path.read_text()))
        except Exception as error:
            errors.append(f"invalid schema {schema_path.name}: {error}")
    if (ROOT / "plugins/gravitas-antigravity/hooks/hooks.json").exists():
        errors.append("legacy plugins/gravitas-antigravity/hooks/hooks.json must be removed (duplicate manifest)")
    manifest = yaml.safe_load((ROOT / "benchmarks/manifest.yaml").read_text())
    lanes = manifest.get("lanes", {})
    task_ids = [task_id for lane in lanes.values() for task_id in lane.get("tasks", [])]
    specs = {path.stem for path in (ROOT / "eval/tasks").glob("*.yaml")}
    if len(lanes) != 10:
        errors.append(f"expected 10 lanes, found {len(lanes)}")
    if manifest.get("meta", {}).get("task_count") != len(task_ids):
        errors.append("manifest task_count does not match registered task slots")
    if len(task_ids) != len(set(task_ids)):
        errors.append("manifest task IDs must be unique")
    if set(task_ids) - specs:
        errors.append(f"missing task specs: {sorted(set(task_ids) - specs)}")
    triggers = json.loads((ROOT / "eval/trigger-eval.json").read_text())
    intended, unintended = triggers.get("intended_activations", []), triggers.get("non_activations", [])
    if not intended or not unintended or not all(item.get("expect") is True for item in intended) or not all(item.get("expect") is False for item in unintended):
        errors.append("trigger evaluation must contain intended and non-activation cases with explicit expectations")
    # Hard-negative gate: near-miss read-only questions must be present,
    # otherwise false-positive rate is meaningless.
    if len(unintended) < 10:
        errors.append(f"trigger evaluation needs >=10 non-activation cases (near-miss included), found {len(unintended)}")
    unintended_text = " ".join(item.get("input", "").lower() for item in unintended)
    if "regex" not in unintended_text and "summarize" not in unintended_text and "stack trace" not in unintended_text:
        errors.append("trigger evaluation must include near-miss read-only cases (explain/summarize, no mutation)")
    # Tier-eval gate: classification accuracy needs a labeled set.
    tier_path = ROOT / "eval/tier-eval.json"
    if not tier_path.is_file():
        errors.append("eval/tier-eval.json is missing")
    else:
        try:
            tier_cases = json.loads(tier_path.read_text()).get("cases", [])
        except (OSError, ValueError) as error:
            errors.append(f"eval/tier-eval.json unreadable: {error}")
            tier_cases = []
        if len(tier_cases) < 30:
            errors.append(f"eval/tier-eval.json needs >=30 labeled cases, found {len(tier_cases)}")
    # Negative-task gate: each NEG task must declare its trap.
    for neg in ("NEG-001", "NEG-002", "NEG-003", "NEG-004", "NEG-005"):
        neg_path = ROOT / "eval/tasks" / f"{neg}.yaml"
        if not neg_path.is_file():
            errors.append(f"eval/tasks/{neg}.yaml is missing")
        elif "fail_condition" not in neg_path.read_text():
            errors.append(f"eval/tasks/{neg}.yaml must declare trap.fail_condition")
    # Trap-task gate: partial-fix / stale-assert / misleading-error coverage.
    for trap in ("TRAP-001", "TRAP-002", "TRAP-003", "TRAP-004", "TRAP-005"):
        trap_path = ROOT / "eval/tasks" / f"{trap}.yaml"
        if not trap_path.is_file():
            errors.append(f"eval/tasks/{trap}.yaml is missing")
        elif "fail_condition" not in trap_path.read_text():
            errors.append(f"eval/tasks/{trap}.yaml must declare trap.fail_condition")
    # Harvested-task gate: every HARV-* task needs a trap + solver-blind validator.
    harv_tasks = sorted((ROOT / "eval/tasks").glob("HARV-*.yaml"))
    if not harv_tasks:
        errors.append("no harvested tasks found (eval/tasks/HARV-*.yaml)")
    for harv_path in harv_tasks:
        if "fail_condition" not in harv_path.read_text():
            errors.append(f"{harv_path.name} must declare trap.fail_condition")
        validator_path = ROOT / "benchmarks/validators" / (harv_path.stem + ".json")
        if not validator_path.is_file():
            errors.append(f"benchmarks/validators/{harv_path.stem}.json is missing (solver-blind hash)")
            continue
        try:
            meta = json.loads(validator_path.read_text())
        except (OSError, ValueError) as error:
            errors.append(f"benchmarks/validators/{harv_path.stem}.json unreadable: {error}")
            continue
        if "hidden_validator_hash" not in meta:
            errors.append(f"benchmarks/validators/{harv_path.stem}.json must contain hidden_validator_hash")
        raw_validator = validator_path.read_text()
        if "assertEqual" in raw_validator or "def test_" in raw_validator:
            errors.append(f"benchmarks/validators/{harv_path.stem}.json must not embed test source")
    # Fix-cycle + judge-calibration gates.
    fix_path = ROOT / "eval/fix-cycle-eval.json"
    if not fix_path.is_file():
        errors.append("eval/fix-cycle-eval.json is missing")
    samples_path = ROOT / "eval/judge-calibration/samples.jsonl"
    if not samples_path.is_file():
        errors.append("eval/judge-calibration/samples.jsonl is missing")
    else:
        lines = [line for line in samples_path.read_text().splitlines() if line.strip()]
        if len(lines) < 20:
            errors.append(f"judge-calibration needs >=20 hand-labeled samples, found {len(lines)}")
    # Harness infra gates.
    for relative in ("benchmarks/runner/harvest.py", "benchmarks/runner/simulated_approver.py",
                     "benchmarks/runner/trigger_eval.py", "benchmarks/runner/tier_eval.py",
                     "benchmarks/runner/implementation.py",
                     "benchmarks/TRACKER.md", "eval/judge_calibration.py"):
        if not (ROOT / relative).is_file():
            errors.append(f"{relative} is missing")

    native_plugin_root = ROOT / "plugins/gravitas-antigravity"
    plugin = json.loads((native_plugin_root / "plugin.json").read_text())
    allowed_plugin_fields = {"$schema", "name", "description"}
    if set(plugin) - allowed_plugin_fields:
        errors.append(f"Antigravity plugin manifest has unsupported fields: {sorted(set(plugin) - allowed_plugin_fields)}")
    if plugin.get("$schema") != "https://antigravity.google/schemas/v1/plugin.json":
        errors.append("plugin.json must use the official Antigravity schema")

    hooks = json.loads((native_plugin_root / "hooks.json").read_text())
    runtime = hooks.get("gravitas-runtime", {})
    expected_hooks = {
        "PreToolUse": "pre_tool.py",
        "PostToolUse": "post_tool.py",
        "PostInvocation": "post_invocation.py",
        "Stop": "stop_gate.py",
    }
    for event, script in expected_hooks.items():
        entries = runtime.get(event)
        if not isinstance(entries, list) or not entries:
            errors.append(f"hooks.json is missing gravitas-runtime.{event}")
            continue
        hook_groups = entries[0].get("hooks", []) if event.endswith("ToolUse") else entries
        if not isinstance(hook_groups, list) or not hook_groups:
            errors.append(f"hooks.json has no command hook for {event}")
            continue
        hook = hook_groups[0]
        hook_type = hook.get("type") if isinstance(hook, dict) else None
        command = hook.get("command", "") if isinstance(hook, dict) else ""
        if hook_type != "command" or script not in command:
            errors.append(f"hooks.json {event} must invoke {script} as a command hook")
        if not (native_plugin_root / "scripts" / script).is_file():
            errors.append(f"missing hook script: {script}")

    canonical_root = ROOT / "skills/gravitas"
    native_plugin = native_plugin_root
    for relative in ("plugin.json", "hooks.json", "scripts/pre_tool.py", "scripts/stop_gate.py"):
        if not (native_plugin / relative).is_file():
            errors.append(f"native plugin is missing {relative}")

    prohibited = {
        "God-tier": "unsupported superlative",
        "Claude-level reliability": "unsupported model comparison",
        "150 paired episodes": "unpublished benchmark result",
        "94.7%": "unpublished benchmark result",
        "+52.6%": "unpublished benchmark result",
    }
    for relative in ("README.md", "docs/FAQ.md", "plugins/gravitas-antigravity/plugin.json", "skills/gravitas/SKILL.md"):
        text = (ROOT / relative).read_text()
        for phrase, reason in prohibited.items():
            if phrase in text:
                errors.append(f"{relative} contains {reason}: {phrase}")
    return errors


def main():
    errors = audit()
    for error in errors:
        print(f"FAIL {error}")
    print(f"Audit {'PASS' if not errors else 'FAIL'}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
