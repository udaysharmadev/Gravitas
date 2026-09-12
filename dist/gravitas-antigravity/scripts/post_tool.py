#!/usr/bin/env python3
"""Gravitas PostToolUse hook.

After every tool call:
1. Records tool execution to evidence ledger
2. Logs failures with retry fingerprint to failures.jsonl
3. Tracks file reads for read-before-write enforcement
4. Records affected files for impact tracking

Input (stdin): JSON with tool_name, tool_input, tool_output, success
Output: Side effects only (writes to .gravitas/sessions/)
"""
import json
import sys
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from session_context import session_dir_for_payload
from evidence_chain import append_evidence


READ_TOOLS = {
    "view_file", "grep_search", "find_by_name", "list_dir"
}

WRITE_TOOLS = {
    "write_to_file", "replace_file_content", "multi_replace_file_content"
}


def tool_call(payload: object) -> tuple[str, dict]:
    """Read the Antigravity 2.x hook payload, with v4-preview compatibility."""
    if not isinstance(payload, dict):
        return "", {}
    call = payload.get("toolCall")
    if isinstance(call, dict):
        name, args = call.get("name"), call.get("args", {})
    else:
        name, args = payload.get("tool_name"), payload.get("tool_input", {})
    if not isinstance(name, str) or not isinstance(args, dict):
        return "", {}
    return name, args


def action_fingerprint(tool_name: str, tool_input: dict) -> str:
    key = json.dumps({"tool": tool_name, "input": tool_input}, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def append_jsonl(path: Path, entry: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


SECRET_PATTERNS = (
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)"), r"\1[REDACTED]"),
    (re.compile(r"\b(?:sk|rk|pk|ghp|github_pat)_[A-Za-z0-9_-]{8,}\b"), "[REDACTED_SECRET]"),
    (re.compile(r"(?i)\b([A-Z][A-Z0-9_]*(?:TOKEN|SECRET|API_KEY|PASSWORD)\s*[:=]\s*)([^\s,;]+)"), r"\1[REDACTED]"),
)


def redact_text(value: object, limit: int = 1000) -> str:
    """Remove common credentials before durable evidence logging."""
    text = str(value)
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text[:limit]


def redact_value(value: object) -> object:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(key): redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def target_file(tool_name: str, tool_input: dict) -> str:
    if tool_name == "view_file":
        return tool_input.get("AbsolutePath", tool_input.get("absolute_path", ""))
    return tool_input.get("TargetFile", tool_input.get("target_file", ""))


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        print("{}")
        return

    tool_name, tool_input = tool_call(payload)
    tool_output = payload.get("tool_output", "")
    success = payload.get("success", not bool(payload.get("error")))
    timestamp = datetime.now(timezone.utc).isoformat()

    session_dir = session_dir_for_payload(payload, create=True)
    fingerprint = action_fingerprint(tool_name, tool_input)

    # Record file reads for read-before-write enforcement
    if tool_name in READ_TOOLS:
        target = target_file(tool_name, tool_input)
        if target:
            append_evidence(session_dir, {
                "source": "read",
                "file": target,
                "timestamp": timestamp
            })

    # Record failures for duplicate prevention
    if not success:
        failure_entry = {
            "tool": tool_name,
            "input_summary": redact_value({k: v for k, v in tool_input.items() if k != "CodeContent"}),
            "fingerprint": fingerprint,
            "error": redact_text(tool_output, limit=500),
            "timestamp": timestamp
        }
        append_jsonl(session_dir / "failures.jsonl", failure_entry)

    # Host hook payloads are telemetry only. Official Antigravity PostToolUse
    # documentation does not promise stdout or exit status, so these records
    # must never satisfy the completion gate. ``validator_runner.py`` owns that.
    if tool_name == "run_command":
        command = tool_input.get("CommandLine", tool_input.get("command", ""))
        source = next((name for name, terms in {
            "test_run": ["vitest", "pytest", "jest", "go test", "cargo test", "rspec", "dotnet test", "mvn test"],
            "lint": ["eslint", "ruff", "clippy", "rubocop"],
            "type_check": ["tsc", "mypy", "cargo check"],
            "build": ["npm run build", "dotnet build", "mvn package"],
        }.items() if any(term in command for term in terms)), None)
        if source:
            output_snippet = redact_text(tool_output)
            append_evidence(session_dir, {
                "source": source,
                "command": command,
                "success": success,
                "output_snippet": output_snippet,
                "evidence": output_snippet,
                "verdict": "PASS" if success else "FAIL",
                "timestamp": timestamp
            })

    # Record file writes
    if tool_name in WRITE_TOOLS:
        target = tool_input.get("TargetFile", tool_input.get("target_file", ""))
        append_evidence(session_dir, {
            "source": "write",
            "file": target,
            "success": success,
            "timestamp": timestamp
        })

    # Antigravity's PostToolUse contract requires an empty JSON object.
    print("{}")


if __name__ == "__main__":
    main()
