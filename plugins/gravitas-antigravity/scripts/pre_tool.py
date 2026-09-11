#!/usr/bin/env python3
"""Gravitas PreToolUse hook.

Enforces before any tool call:
1. Action lock (mode vs tool category)
2. Write scope guard (allowed_write_scope)
3. Read-before-write check
4. Duplicate failed action prevention
5. Destructive operation confirmation

Input (stdin): Antigravity JSON with toolCall.name and toolCall.args
Output (stdout): JSON with decision: allow|deny|force_ask and an optional reason
"""
import json
import sys
import hashlib
import re
from pathlib import Path
from session_context import session_dir_for_payload

# Tool categories
READ_ONLY_TOOLS = {
    "view_file", "grep_search", "find_by_name", "list_dir",
    "read_url_content", "search_web"
}

WRITE_TOOLS = {
    "write_to_file", "replace_file_content", "multi_replace_file_content"
}

# Modes that deny all writes
READ_ONLY_MODES = {"answer", "research", "plan-only", "review-only", "security-review"}
MUTATING_COMMAND = re.compile(
    r"(?:^|[;&|]\s*)(?:rm|mv|cp|touch|mkdir|"
    r"git\s+(?:add|commit|push|merge|rebase|reset|clean|checkout|restore)|"
    r"npm\s+(?:install|publish)|pip\s+install|(?:python|python3|node)\s+-c)\b|(?:^|\s)(?:>|>>)"
)
DESTRUCTIVE_COMMAND = re.compile(r"(?:^|[;&|]\s*)(?:rm\b|git\s+reset\b|git\s+clean\b|drop\s+(?:table|database)\b)", re.I)


def load_contract(session_dir: Path) -> dict:
    contract_path = session_dir / "contract.json"
    if contract_path.exists():
        with open(contract_path) as f:
            return json.load(f)
    return {}


def load_failures(session_dir: Path) -> list:
    failures_path = session_dir / "failures.jsonl"
    if not failures_path.exists():
        return []
    failures = []
    with open(failures_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    failures.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return failures


def load_reads(session_dir: Path) -> set:
    """Load set of files read this session from evidence ledger."""
    reads = set()
    evidence_path = session_dir / "evidence.jsonl"
    if not evidence_path.exists():
        return reads
    with open(evidence_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    if entry.get("source") == "read" and entry.get("file"):
                        reads.add(entry["file"])
                except json.JSONDecodeError:
                    pass
    return reads


def action_fingerprint(tool_name: str, tool_input: dict) -> str:
    """Hash of tool + key inputs for retry detection."""
    key = json.dumps({"tool": tool_name, "input": tool_input}, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def command_text(tool_input: dict) -> str:
    return str(tool_input.get("CommandLine", tool_input.get("command", "")))


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


def workspace_roots(payload: object) -> list[Path]:
    """Use host-declared workspace roots when present; never trust process cwd."""
    if isinstance(payload, dict):
        raw_roots = payload.get("workspacePaths") or payload.get("workspace_paths")
        if isinstance(raw_roots, list):
            roots = [Path(value).resolve(strict=False) for value in raw_roots if isinstance(value, str) and value]
            if roots:
                return roots
    # Legacy payload compatibility only. Native payloads should include roots.
    return [Path.cwd().resolve()]


def target_in_scope(target: str, scopes: list[str], roots: list[Path]) -> bool:
    target_path = Path(target).resolve(strict=False)
    if not Path(target).is_absolute():
        # A relative tool argument is permitted only when every candidate is
        # anchored in an explicitly declared workspace root.
        candidates = [(root / target).resolve(strict=False) for root in roots]
    else:
        candidates = [target_path]
    for scope in scopes:
        for root in roots:
            scope_path = (root / scope).resolve(strict=False) if not Path(scope).is_absolute() else Path(scope).resolve(strict=False)
            for candidate in candidates:
                try:
                    candidate.relative_to(scope_path)
                    return True
                except ValueError:
                    continue
    return False


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        print(json.dumps({
            "decision": "deny",
            "reason": "Gravitas could not parse the PreToolUse payload; denied fail-closed."
        }))
        return

    tool_name, tool_input = tool_call(payload)
    if not tool_name:
        print(json.dumps({
            "decision": "deny",
            "reason": "Gravitas received a PreToolUse payload without toolCall.name."
        }))
        return

    session_dir = session_dir_for_payload(payload)
    contract = load_contract(session_dir) if session_dir else {}
    mode = contract.get("mode", "implement")
    command = command_text(tool_input) if tool_name == "run_command" else ""

    # A native conversation without an initialized contract is deliberately
    # unable to mutate. This prevents one task from inheriting another task's
    # policy via a "latest session" fallback.
    if payload.get("conversationId") and not (session_dir and (session_dir / "contract.json").exists()):
        if tool_name in WRITE_TOOLS or command:
            print(json.dumps({"decision": "deny", "reason": "Native session is not initialized with a Gravitas contract; mutations and shell commands fail closed."}))
            return

    if tool_name in WRITE_TOOLS and not session_dir:
        target = tool_input.get("TargetFile", tool_input.get("target_file", ""))
        if target and Path(target).resolve(strict=False).exists():
            print(json.dumps({
                "decision": "deny",
                "reason": "Read-before-write violation: no Gravitas session has recorded a read of this existing file."
            }))
            return

    # 1. Action lock: deny writes in read-only modes
    if (tool_name in WRITE_TOOLS or (command and MUTATING_COMMAND.search(command))) and mode in READ_ONLY_MODES:
        print(json.dumps({
            "decision": "deny",
            "reason": f"Action lock: mode={mode} does not permit {tool_name}. "
                      f"Task contract mode '{mode}' is read-only. "
                      f"To perform writes, change the task mode to 'implement'."
        }))
        return

    # 2. Write scope guard
    allowed_scope = contract.get("allowed_write_scope", [])
    if allowed_scope and tool_name in WRITE_TOOLS:
        target = tool_input.get("TargetFile", tool_input.get("target_file", ""))
        if target:
            in_scope = target_in_scope(target, allowed_scope, workspace_roots(payload))
            if not in_scope:
                print(json.dumps({
                    "decision": "deny",
                    "reason": f"Scope violation: {target} is outside allowed_write_scope {allowed_scope}. "
                              f"Update the task contract to include this path if the write is intentional."
                }))
                return


    # 3. Destructive operations require an explicit contract-scoped confirmation.
    if command and DESTRUCTIVE_COMMAND.search(command):
        print(json.dumps({
            "decision": "force_ask",
            "reason": "Destructive operation requires explicit user confirmation."
        }))
        return

    # 4. Read-before-write check
    if tool_name in WRITE_TOOLS and session_dir:
        target = tool_input.get("TargetFile", tool_input.get("target_file", ""))
        if target:
            reads = load_reads(session_dir)
            # Normalize path for comparison
            target_path = Path(target).resolve(strict=False)
            read_paths = {Path(r).resolve(strict=False) for r in reads}
            if target_path.exists() and target_path not in read_paths:
                print(json.dumps({
                    "decision": "deny",
                    "reason": f"Read-before-write violation: {target} has not been read this session. "
                              f"Read the file before editing it (Rule 1)."
                }))
                return

    # 5. Duplicate failed action prevention
    if session_dir:
        failures = load_failures(session_dir)
        fingerprint = action_fingerprint(tool_name, tool_input)
        failed_fingerprints = {f.get("fingerprint") for f in failures}
        if fingerprint in failed_fingerprints:
            print(json.dumps({
                "decision": "deny",
                "reason": f"Duplicate failed action: this exact operation failed previously this session. "
                          f"Check failures.jsonl for the reason. Try a different approach."
            }))
            return

    # Allow through
    print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
