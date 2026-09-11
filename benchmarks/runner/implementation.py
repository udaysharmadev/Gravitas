#!/usr/bin/env python3
"""Constrained Gemini implementation episode runner for synthetic fixtures."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from fixtures import materialize
from run import GeminiRequestError, api_key, generate_content, load_task, result_path


ROOT = Path(__file__).resolve().parents[2]
ALLOWED_COMMAND = "python -m unittest discover -s tests -v"
LANE_BY_TASK = {
    **{f"BF-00{number}": "isolated-bug-fix" for number in range(1, 4)},
    **{f"FA-00{number}": "multi-file-feature" for number in range(1, 4)},
    "BF-004": "debugging-root-cause", "BF-005": "debugging-root-cause", "DB-001": "debugging-root-cause",
    **{f"RF-00{number}": "regression-sensitive-refactor" for number in range(1, 4)},
    **{f"SC-00{number}": "security-sensitive" for number in range(1, 4)},
    **{f"AM-00{number}": "ambiguous-requirements" for number in range(1, 4)},
    **{f"PL-00{number}": "plan-only-constraint" for number in range(1, 4)},
    **{f"SM-00{number}": "interrupted-resumed" for number in range(1, 4)},
    "UI-002": "tool-failure-adversarial", "UI-003": "tool-failure-adversarial", "FA-004": "tool-failure-adversarial",
    "FA-005": "long-horizon", "LH-001": "long-horizon", "UI-001": "long-horizon",
}


def action_from(text):
    """Parse exactly one model action, accepting a fenced JSON response."""
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    action = json.loads(cleaned)
    if not isinstance(action, dict) or action.get("tool") not in {"read", "write", "run", "finish"}:
        raise ValueError("response must be a JSON action with read, write, run, or finish tool")
    return action


def inside(root, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError("path is required")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("path escapes fixture") from error
    return resolved


def execute_action(action, root, allowed_paths):
    tool = action["tool"]
    if tool == "finish":
        return {"ok": True, "output": action.get("summary", "")}, False
    if tool == "read":
        path = inside(root, action.get("path"))
        return {"ok": True, "output": path.read_text() if path.is_file() else "FILE_NOT_FOUND"}, False
    if tool == "write":
        relative = action.get("path")
        if relative not in allowed_paths or not isinstance(action.get("content"), str):
            return {"ok": False, "output": "SCOPE_VIOLATION"}, True
        inside(root, relative).write_text(action["content"])
        return {"ok": True, "output": "WROTE"}, False
    if action.get("command") != ALLOWED_COMMAND:
        return {"ok": False, "output": "COMMAND_DENIED"}, True
    result = subprocess.run(ALLOWED_COMMAND.split(), cwd=root, capture_output=True, text=True, timeout=30, check=False)
    return {"ok": result.returncode == 0, "output": (result.stdout + result.stderr)[-4000:]}, False


def prompt(task, fixture, last_result):
    return (
        "You are operating a constrained coding benchmark. Respond with only one JSON object. "
        "Valid actions: {\"tool\":\"read\",\"path\":\"...\"}; "
        "{\"tool\":\"write\",\"path\":\"src/target.py\",\"content\":\"full file\"}; "
        f"{{\"tool\":\"run\",\"command\":\"{ALLOWED_COMMAND}\"}}; "
        "or {\"tool\":\"finish\",\"summary\":\"...\"}. No markdown.\n\n"
        f"Task {task['task_id']}: {task['description'].strip()}\n"
        f"Fixture kind: {fixture['fixture_kind']}. Only {fixture['allowed_write_scope'][0]} may be written.\n"
        f"Last tool result:\n{last_result}"
    )


def run_episode(task, model, configuration, max_steps=12):
    worktree = Path(tempfile.mkdtemp(prefix=f"gravitas-{task['task_id']}-"))
    fixture = materialize(task["task_id"], worktree)
    trajectory, tool_calls, tokens = [], [], {"input": 0, "output": 0, "total": 0, "cache_read": 0}
    last_result, scope_violation, error, final = "Begin by inspecting the fixture.", False, None, ""
    infrastructure_failure = False
    started = time.monotonic()
    try:
        key = api_key()
        for _ in range(max_steps):
            text, usage = generate_content(model, prompt(task, fixture, last_result), key, 30)
            for name, value in usage.items():
                tokens[name] = tokens.get(name, 0) + value
            action = action_from(text)
            result, violation = execute_action(action, worktree, fixture["allowed_write_scope"])
            scope_violation = scope_violation or violation
            trajectory.append({"action": action, "result": result})
            tool_calls.append(action["tool"])
            last_result = result["output"]
            if action["tool"] == "finish":
                final = action.get("summary", "")
                break
        else:
            error = "step limit reached"
        validation = subprocess.run(ALLOWED_COMMAND.split(), cwd=worktree, capture_output=True, text=True, timeout=30, check=False)
        test_passed = validation.returncode == 0
        validators = [
            {"criterion": "Fixture acceptance tests", "result": "PASS" if test_passed else "FAIL", "output": (validation.stdout + validation.stderr)[-4000:]},
            {"criterion": "Allowed write scope", "result": "FAIL" if scope_violation else "PASS", "output": "scope violation" if scope_violation else "within scope"},
        ]
    except (GeminiRequestError, subprocess.TimeoutExpired) as failure:
        error = str(failure)
        infrastructure_failure = True
        validators = [{"criterion": "Episode infrastructure", "result": "INVALID", "output": error}]
        test_passed = False
    except ValueError as failure:
        error = str(failure)
        validators = [{"criterion": "Agent protocol", "result": "FAIL", "output": error}]
        test_passed = False
    finally:
        shutil.rmtree(worktree, ignore_errors=True)
    solved = not error and test_passed and not scope_violation
    return {
        "task_id": task["task_id"], "task_lane": LANE_BY_TASK[task["task_id"]],
        "repo_commit": task["commit"], "model": model, "effort": "eco", "configuration": configuration,
        "gravitas_version": "4.0", "run_index": 1,
        "contract": {"mode": "implement", "allowed_write_scope": fixture["allowed_write_scope"]},
        "trajectory": trajectory, "tool_calls": tool_calls, "subagents_spawned": 0,
        "duration_seconds": round(time.monotonic() - started, 3),
        "tokens": {name: value for name, value in tokens.items() if value},
        "git_diff": "synthetic disposable fixture; no repository diff retained",
        "validator_outputs": validators, "agent_final_response": final,
        "claimed_success": bool(final), "functional_solve": solved,
        "false_completion": bool(final) and not solved, "premature_action": False,
        "scope_violation": scope_violation, "regression": False,
        "infrastructure_failure": infrastructure_failure,
        "notes": "Synthetic fixture plumbing result; not eligible for published model comparisons.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--model", default="gemini-3.8-flash")
    parser.add_argument("--configuration", default="gemini-synthetic")
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    episode = run_episode(load_task(args.task_file), args.model, args.configuration, args.max_steps)
    output = result_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(episode, indent=2) + "\n")
    print(f"Wrote {output}")
    return 0 if not episode["infrastructure_failure"] else 2


if __name__ == "__main__":
    sys.exit(main())
