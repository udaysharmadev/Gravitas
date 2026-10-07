#!/usr/bin/env python3
"""Normalized host action/event model for the Gravitas runtime.

Core policy consumes :class:`Action`, never host tool names. Each host
adapter translates its native payloads into this model:

- Antigravity hook payloads -> :func:`antigravity_envelope`
- OpenCode events -> ``opencode_envelope`` (Phase 7; interface defined here)

Capability levels, weakest to strongest:

- ``none``: provably read-only (file view, status query).
- ``write``: mutates files or state, but inside an enumerable scope.
- ``mutation``: executes code or mutates through paths the runtime cannot
  enumerate (shell pipelines, interpreters, package installs).
- ``destructive``: deletes, overwrites blindly, touches infrastructure, or
  exfiltrates (network upload, cloud/infra CLIs).

Shell classification is tokenizer-based (shlex + operator scan), not a
denylist regex: unparsable input fails closed to ``mutation`` at minimum.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

#: Ordered capability levels.
LEVELS = ("none", "write", "mutation", "destructive")

#: Action kinds.
KINDS = ("read", "write", "execute", "network", "other")


@dataclass
class Action:
    kind: str
    tool: str
    paths: list = field(default_factory=list)
    cwd: str = ""
    executable: str = ""
    argv: list = field(default_factory=list)
    raw_command: str = ""
    mutation: str = "none"
    network_target: str = ""
    host_metadata: dict = field(default_factory=dict)


@dataclass
class HostEnvelope:
    """Host-agnostic event envelope handed to policy evaluation."""

    tool: str
    args: dict
    conversation_id: str = ""
    workspace_roots: list = field(default_factory=list)
    host: str = ""
    event: str = "before_action"


# ---------------------------------------------------------------------------
# Host tool classification (Antigravity vocabulary; OpenCode maps onto this).
# ---------------------------------------------------------------------------

READ_TOOLS = frozenset({
    "view_file", "grep_search", "find_by_name", "list_dir",
    "read_url_content", "search_web",
})

WRITE_TOOLS = frozenset({
    "write_to_file", "replace_file_content", "multi_replace_file_content",
})

#: Aliases observed on real hosts (fixture-pinned in tests/fixtures/).
#: Unknown tool names normalize to kind "other": visible, never gated.
TOOL_ALIASES = {
    "edit_file": "write_to_file",
    "write_file": "write_to_file",
    "create_file": "write_to_file",
}

SHELL_TOOLS = frozenset({"run_command"})


def canonical_tool(tool: str) -> str:
    return TOOL_ALIASES.get(tool, tool)


def target_file(tool: str, args: dict) -> str:
    tool = canonical_tool(tool)
    if tool == "view_file":
        return str(args.get("AbsolutePath", args.get("absolute_path", "")))
    if tool == "list_dir":
        return str(args.get("DirectoryPath", args.get("directory_path", "")))
    return str(args.get("TargetFile", args.get("target_file", "")))


def command_text(args: dict) -> str:
    return str(args.get("CommandLine", args.get("command", "")))


# ---------------------------------------------------------------------------
# Shell classification.
# ---------------------------------------------------------------------------

#: Binaries whose bare invocation the runtime treats as read-only execution.
READ_BINARIES = frozenset({
    "ls", "cat", "head", "tail", "grep", "rg", "find", "git-status",
    "echo", "pwd", "which", "wc", "diff", "jq",
})

#: Read-only git subcommands. Every other git subcommand mutates or worse.
READ_GIT = frozenset({"status", "diff", "log", "show", "branch", "stash-list"})

#: Test/type/lint/build-check commands: execute code but declare no writes.
CHECK_COMMANDS = (
    "pytest", "vitest", "jest", "go test", "cargo test", "rspec",
    "dotnet test", "mvn test", "tsc", "mypy", "eslint", "ruff",
    "clippy", "rubocop", "cargo check", "npm run build", "dotnet build",
)

#: Executables that always escalate: infra CLIs, network fetchers, raw writers.
DESTRUCTIVE_BINARIES = frozenset({
    "dd", "truncate", "tee", "chmod", "chown",
    "docker", "kubectl", "terraform", "aws", "gcloud", "az",
    "curl", "wget", "ssh", "scp", "rsync",
})

DESTRUCTIVE_GIT = frozenset({"reset", "clean", "checkout", "restore", "rm"})

_SUBSTITUTION = re.compile(r"\$\(|`[^`]*`")
_REDIRECT = re.compile(r"(?:^|[\s\d])(?:>>?|<)(?=\s|$|=)")
_PIPE = re.compile(r"\|")


def _basename(argv0: str) -> str:
    return argv0.rsplit("/", 1)[-1]


def _operand_paths(segment: str) -> list[str]:
    """Extract enumerable file operands (tee targets, dd of=).

    Heuristic and incomplete by design: code-execution side effects
    (interpreters, test runners) have no enumerable paths and are handled
    by capability level, not scope.
    """
    try:
        argv = shlex.split(segment, posix=True)
    except ValueError:
        return []
    if not argv:
        return []
    binary = _basename(argv[0])
    rest = argv[1:]
    if binary == "tee":
        return [arg for arg in rest if not arg.startswith("-") and arg not in ("--",)]
    if binary == "dd":
        return [arg[3:] for arg in rest if arg.startswith("of=") and len(arg) > 3]
    return []


def classify_shell_segment(segment: str) -> dict:
    """Classify one pipeline segment (no top-level | ; &)."""
    try:
        argv = shlex.split(segment, posix=True)
    except ValueError:
        return {"mutation": "mutation", "reason": "unparsable shell segment fails closed"}
    if not argv:
        return {"mutation": "none", "reason": "empty segment"}
    binary = _basename(argv[0])
    rest = argv[1:]

    if binary in DESTRUCTIVE_BINARIES:
        return {"mutation": "destructive", "executable": binary, "argv": argv,
                "reason": f"{binary} is never read-only"}
    if binary == "git":
        sub = rest[0] if rest else ""
        if sub in DESTRUCTIVE_GIT:
            return {"mutation": "destructive", "executable": "git", "argv": argv,
                    "reason": f"git {sub} destroys or overwrites state"}
        if sub in {"add", "commit", "push", "merge", "rebase"}:
            return {"mutation": "mutation", "executable": "git", "argv": argv,
                    "reason": f"git {sub} mutates repository state"}
        if sub in READ_GIT or sub == "stash" and rest[1:2] == ["list"]:
            return {"mutation": "none", "executable": "git", "argv": argv,
                    "reason": f"git {sub} is a read-only query"}
        return {"mutation": "mutation", "executable": "git", "argv": argv,
                "reason": "unknown git subcommand fails closed"}
    if binary in {"rm", "mv"}:
        return {"mutation": "destructive", "executable": binary, "argv": argv,
                "reason": f"{binary} deletes or moves state"}
    if binary in {"cp", "touch", "mkdir", "ln", "sed", "patch", "tar", "unzip", "zip", "install",
                   "ed", "ex", "vi", "vim", "nano", "emacs"}:
        if binary == "sed" and not any(arg == "-i" or arg.startswith("-i") or arg == "--in-place" for arg in rest):
            return {"mutation": "none", "executable": binary, "argv": argv,
                    "reason": "sed without -i only filters text"}
        return {"mutation": "mutation", "executable": binary, "argv": argv,
                "reason": f"{binary} writes files"}
    if binary in {"python", "python3", "node", "deno", "ruby", "php", "perl", "bash", "sh"}:
        if rest[:1] in (["-c"], ["-e"], ["--eval"]):
            return {"mutation": "mutation", "executable": binary, "argv": argv,
                    "reason": f"{binary} {rest[0]} executes arbitrary code"}
        for flag in ("-m",):
            if rest[:1] == [flag]:
                return {"mutation": "mutation", "executable": binary, "argv": argv,
                        "reason": f"{binary} {flag} executes a module"}
        if any(arg.endswith(".py") or arg.endswith(".js") for arg in rest):
            return {"mutation": "mutation", "executable": binary, "argv": argv,
                    "reason": f"{binary} runs a script file"}
        return {"mutation": "none", "executable": binary, "argv": argv,
                "reason": f"{binary} version/flag query"}
    if binary in {"npm", "pip", "pip3", "yarn", "pnpm", "cargo", "go"}:
        verb = rest[0] if rest else ""
        if verb in {"install", "publish", "add", "remove", "uninstall", "test", "run"}:
            return {"mutation": "mutation", "executable": binary, "argv": argv,
                    "reason": f"{binary} {verb} changes state or executes project code"}
        if verb in {"", "ls", "list", "view", "show", "freeze", "check", "--version", "version"}:
            return {"mutation": "none", "executable": binary, "argv": argv,
                    "reason": f"{binary} {verb or 'query'} is read-only"}
        return {"mutation": "mutation", "executable": binary, "argv": argv,
                "reason": f"{binary} {verb} is not a known read-only verb; fails closed"}
    if binary == "find":
        if "-delete" in rest or "-exec" in rest:
            return {"mutation": "destructive", "executable": binary, "argv": argv,
                    "reason": "find -delete/-exec acts on the tree"}
        return {"mutation": "none", "executable": binary, "argv": argv,
                "reason": "find query is read-only"}
    if binary == "echo":
        return {"mutation": "none", "executable": binary, "argv": argv,
                "reason": "echo without redirection only writes stdout"}
    if binary in READ_BINARIES:
        return {"mutation": "none", "executable": binary, "argv": argv,
                "reason": f"{binary} is a read-only query"}
    for check in CHECK_COMMANDS:
        parts = check.split()
        if argv[: len(parts)] == parts or (len(parts) == 1 and binary == parts[0]):
            return {"mutation": "mutation", "executable": argv[0], "argv": argv,
                    "reason": f"{check} executes project code (side effects possible)"}
    if binary == "drop" or "drop table" in segment.lower() or "drop database" in segment.lower():
        return {"mutation": "destructive", "executable": binary, "argv": argv,
                "reason": "destructive database statement"}
    return {"mutation": "mutation", "executable": binary, "argv": argv,
            "reason": f"unknown executable {binary!r} fails closed"}


def classify_shell(command: str) -> dict:
    """Classify a full shell command line. Worst segment wins."""
    text = command.strip()
    if not text:
        return {"mutation": "none", "reason": "empty command"}
    segments = [seg for seg in re.split(r"[;&|]+", text) if seg.strip()]
    worst = "none"
    reasons = []
    executable = ""
    argv: list = []
    paths: list = []
    network = bool(re.search(r"\bcurl\b|\bwget\b|\bssh\b|\bscp\b", text))
    if _SUBSTITUTION.search(text):
        # Floor, not verdict: substitution executes nested code, but the
        # outer segments may still be destructive (e.g. curl $(id)).
        worst = "mutation"
        reasons.append("command substitution executes nested code")
    if _PIPE.search(text):
        worst = "mutation"
        reasons.append("pipeline moves data between processes")
    if _REDIRECT.search(text):
        worst = "mutation"
        reasons.append("redirection writes outside argv")
        for match in re.finditer(r"(?:>|>>|<)\s*(\S+)", text):
            paths.append(match.group(1))
    for segment in segments:
        operand_paths = _operand_paths(segment)
        for operand in operand_paths:
            if operand not in paths:
                paths.append(operand)
    for segment in segments:
        result = classify_shell_segment(segment)
        if LEVELS.index(result["mutation"]) > LEVELS.index(worst):
            worst = result["mutation"]
            executable = result.get("executable", "")
            argv = result.get("argv", [])
        reasons.append(result.get("reason", ""))
    if network and LEVELS.index(worst) < LEVELS.index("destructive"):
        if "|" in text or "sh" in text.split():
            worst = "destructive"
            reasons.append("network fetch piped to execution")
    return {
        "mutation": worst,
        "reason": "; ".join(dict.fromkeys(reasons)),
        "executable": executable,
        "argv": argv,
        "paths": paths,
        "network": network,
    }


# ---------------------------------------------------------------------------
# Normalization entry points.
# ---------------------------------------------------------------------------

def normalize(tool: str, args: dict, *, host_metadata: dict | None = None) -> Action:
    """Build a normalized Action from a host tool call."""
    meta = dict(host_metadata or {})
    tool = canonical_tool(tool)
    if tool in READ_TOOLS:
        return Action(kind="read", tool=tool, paths=[p for p in [target_file(tool, args)] if p],
                      mutation="none", host_metadata=meta)
    if tool in WRITE_TOOLS:
        return Action(kind="write", tool=tool, paths=[p for p in [target_file(tool, args)] if p],
                      mutation="write", host_metadata=meta)
    if tool in SHELL_TOOLS:
        command = command_text(args)
        result = classify_shell(command)
        kind = "network" if result.get("network") else "execute"
        return Action(kind=kind, tool=tool, paths=result.get("paths", []),
                      executable=result.get("executable", ""), argv=result.get("argv", []),
                      raw_command=command, mutation=result["mutation"],
                      network_target="network" if result.get("network") else "",
                      host_metadata={**meta, "shell_reason": result.get("reason", "")})
    return Action(kind="other", tool=tool, mutation="none", host_metadata=meta)


def antigravity_envelope(payload: object) -> tuple[HostEnvelope, Action] | tuple[None, None]:
    """Translate an Antigravity hook payload into (envelope, action).

    Returns (None, None) when the payload carries no intelligible tool call;
    callers fail closed.
    """
    if not isinstance(payload, dict):
        return None, None
    call = payload.get("toolCall")
    if isinstance(call, dict):
        name, args = call.get("name"), call.get("args", {})
    else:
        name, args = payload.get("tool_name"), payload.get("tool_input", {})
    if not isinstance(name, str) or not isinstance(args, dict):
        return None, None
    raw_roots = payload.get("workspacePaths") or payload.get("workspace_paths") or []
    roots = [str(value) for value in raw_roots if isinstance(value, str) and value]
    conversation = payload.get("conversationId") or payload.get("conversation_id") or ""
    envelope = HostEnvelope(tool=canonical_tool(name), args=args,
                            conversation_id=conversation if isinstance(conversation, str) else "",
                            workspace_roots=roots, host="antigravity",
                            event=str(payload.get("hookEventName",
                                                  payload.get("hookEvent", "before_action"))))
    action = normalize(name, args, host_metadata={"conversation_id": envelope.conversation_id})
    return envelope, action


def workspace_roots(envelope: HostEnvelope | None) -> list[Path]:
    if envelope and envelope.workspace_roots:
        return [Path(value).resolve(strict=False) for value in envelope.workspace_roots]
    return [Path.cwd().resolve()]


def confine_cwd(raw: str) -> Path:
    """Resolve a runner --cwd and refuse escape from the invoking directory.

    Owned execution (validator_runner, repro_runner) must not be steered
    to /etc, $HOME, or sibling checkouts via --cwd. The directory must
    exist inside the process working directory after symlink resolution.
    Raises ValueError on escape.
    """
    import os
    base = os.path.realpath(os.getcwd())
    candidate = os.path.realpath(os.path.join(base, raw))
    if candidate != base and not candidate.startswith(base + os.sep):
        raise ValueError(f"--cwd escapes the workspace: {raw!r} resolves outside {base}")
    resolved = Path(candidate)
    if not resolved.is_dir():
        raise ValueError(f"--cwd is not a directory: {raw!r}")
    return resolved
