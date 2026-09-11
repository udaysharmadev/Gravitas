#!/usr/bin/env python3
"""Validate GravitasBench schemas, task registry, and trigger-eval dataset."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def audit():
    import yaml
    from jsonschema import Draft7Validator

    errors = []
    for schema_path in sorted((ROOT / "schemas").glob("*.schema.json")):
        try:
            Draft7Validator.check_schema(json.loads(schema_path.read_text()))
        except Exception as error:
            errors.append(f"invalid schema {schema_path.name}: {error}")
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

    plugin = json.loads((ROOT / "plugin.json").read_text())
    allowed_plugin_fields = {"$schema", "name", "description"}
    if set(plugin) - allowed_plugin_fields:
        errors.append(f"Antigravity plugin manifest has unsupported fields: {sorted(set(plugin) - allowed_plugin_fields)}")
    if plugin.get("$schema") != "https://antigravity.google/schemas/v1/plugin.json":
        errors.append("plugin.json must use the official Antigravity schema")

    hooks = json.loads((ROOT / "hooks.json").read_text())
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
        if not (ROOT / "plugins/gravitas-antigravity/scripts" / script).is_file():
            errors.append(f"missing hook script: {script}")

    canonical_root = ROOT / "skills/gravitas"
    activation_root = ROOT / ".agents/skills/gravitas"
    canonical_files = {
        path.relative_to(canonical_root)
        for path in canonical_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    activation_files = {
        path.relative_to(activation_root)
        for path in activation_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    if canonical_files != activation_files:
        errors.append(".agents activation bundle file set must match the canonical skill bundle")
    for relative in sorted(canonical_files & activation_files):
        if (canonical_root / relative).read_bytes() != (activation_root / relative).read_bytes():
            errors.append(f".agents activation copy is stale: {relative}")

    prohibited = {
        "God-tier": "unsupported superlative",
        "Claude-level reliability": "unsupported model comparison",
        "150 paired episodes": "unpublished benchmark result",
        "94.7%": "unpublished benchmark result",
        "+52.6%": "unpublished benchmark result",
    }
    for relative in ("README.md", "docs/FAQ.md", "plugin.json", "skills/gravitas/SKILL.md"):
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
