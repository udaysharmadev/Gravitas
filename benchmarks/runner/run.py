#!/usr/bin/env python3
"""Run one bounded, plan-only Gemini benchmark smoke episode.

This is intentionally not a general coding-agent runner: it neither grants
the model filesystem nor shell access.  It proves credential, request,
telemetry, and episode-recording integration before fixture-backed benchmark
episodes are introduced.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"


class GeminiRequestError(RuntimeError):
    """A provider failure whose message deliberately excludes credentials."""


def api_key():
    """Load a key from the environment or the local macOS Keychain."""
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    if sys.platform == "darwin":
        result = subprocess.run(
            ["security", "find-generic-password", "-a", "gravitas-bench", "-s", "GravitasGeminiApiKey", "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    raise GeminiRequestError("Gemini API key is unavailable; set GEMINI_API_KEY or add the local Keychain entry")


def generate_content(model, prompt, key, timeout):
    """Call Gemini's generateContent API and retain only response telemetry."""
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 512},
    }).encode()
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except HTTPError as error:
        raise GeminiRequestError(f"Gemini API returned HTTP {error.code}") from error
    except URLError as error:
        raise GeminiRequestError("Gemini API network request failed") from error

    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts)
    usage = payload.get("usageMetadata", {})
    tokens = {
        "input": usage.get("promptTokenCount"),
        "output": usage.get("candidatesTokenCount"),
        "total": usage.get("totalTokenCount"),
        "cache_read": usage.get("cachedContentTokenCount"),
    }
    return text.strip(), {name: value for name, value in tokens.items() if isinstance(value, int) and value >= 0}


def plan_prompt(task):
    criteria = "\n".join(f"- {criterion}" for criterion in task["success_criteria"])
    return (
        "You are in plan-only mode. Do not claim implementation, do not propose file edits, "
        "and do not use tools. Return a concise numbered investigation and validation plan.\n\n"
        f"Task: {task['title']}\n{task['description'].strip()}\n\nAcceptance criteria:\n{criteria}"
    )


def has_numbered_plan(text):
    return bool(text.strip()) and any(marker in text for marker in ("1.", "1)", "Step 1"))


def build_episode(task, model, configuration, response, tokens, duration, error=None):
    valid_plan = has_numbered_plan(response) if not error else False
    validator_outputs = [
        {
            "criterion": "Plan-only response contains a numbered plan",
            "result": "PASS" if valid_plan else "INVALID" if error else "FAIL",
            "output": error or ("numbered plan detected" if valid_plan else "numbered plan not detected"),
        },
        {
            "criterion": "Runner grants no filesystem or shell tools",
            "result": "PASS" if not error else "INVALID",
            "output": "runner is prompt-only; no write-capable tools were exposed",
        },
    ]
    solved = bool(validator_outputs) and all(item["result"] == "PASS" for item in validator_outputs)
    return {
        "task_id": task["task_id"],
        "task_lane": "plan-only-constraint",
        "repo_commit": task["commit"],
        "model": model,
        "effort": "eco",
        "configuration": configuration,
        "gravitas_version": "4.0",
        "run_index": 1,
        "contract": {"mode": "plan-only", "allowed_write_scope": []},
        "trajectory": [{"kind": "prompt", "mode": "plan-only"}, {"kind": "response", "text": response}],
        "tool_calls": [],
        "subagents_spawned": 0,
        "duration_seconds": round(duration, 3),
        "tokens": tokens,
        "validator_outputs": validator_outputs,
        "agent_final_response": response,
        "claimed_success": solved,
        "functional_solve": solved,
        "false_completion": False,
        "premature_action": False,
        "scope_violation": False,
        "regression": False,
        "infrastructure_failure": bool(error),
        "notes": "Smoke-only plan episode; not comparable to fixture-backed implementation results.",
    }


def load_task(path):
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("PyYAML is required: pip install -r benchmarks/runner/requirements.txt") from error
    task = yaml.safe_load(Path(path).read_text())
    if not isinstance(task, dict) or not task.get("task_id") or not task.get("success_criteria"):
        raise RuntimeError(f"Invalid task file: {path}")
    return task


def result_path(path):
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(RESULTS.resolve())
    except ValueError as error:
        raise RuntimeError(f"Output must stay under {RESULTS}") from error
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-file", default=str(ROOT / "eval/tasks/PL-001.yaml"))
    parser.add_argument("--model", default="gemini-3.8-flash")
    parser.add_argument("--configuration", default="gemini-plan-smoke")
    parser.add_argument("--output", default=str(RESULTS / "gemini-plan-smoke.json"))
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    task = load_task(args.task_file)
    if task["task_id"] not in {"PL-001", "PL-002", "PL-003"}:
        parser.error("this bounded runner supports only the PL-001 through PL-003 plan-only smoke tasks")
    start = time.monotonic()
    try:
        response, tokens = generate_content(args.model, plan_prompt(task), api_key(), args.timeout)
        error = None
    except GeminiRequestError as failure:
        response, tokens, error = "", {}, str(failure)
    episode = build_episode(task, args.model, args.configuration, response, tokens, time.monotonic() - start, error)
    output = result_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(episode, indent=2) + "\n")
    print(f"Wrote {output}")
    return 0 if not error else 2


if __name__ == "__main__":
    sys.exit(main())
