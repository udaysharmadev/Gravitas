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

import os
import re
import shlex
import sys
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
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

#: Read-only git subcommands (flagless only; flags are inspected separately).
READ_GIT = frozenset({"status", "diff", "log", "show", "stash-list"})

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

#: git config keys (via `git -c`) that make read-only subcommands run programs.
_GIT_EXEC_CONFIG = ("external", "pager", "command", "fsmonitor", "editor", "helper",
                    "alias.", "hook", "textconv", "include.", "includeif.", "askpass")

DESTRUCTIVE_GIT = frozenset({"reset", "clean", "checkout", "restore", "rm"})

_SUBSTITUTION = re.compile(r"\$\(|`[^`]*`|[<>]\(")
_REDIRECT = re.compile(r"(?<![-=<])(?:(?:>>?|&>>?)(?![(=>])(?:\s|$|&[\d-]|[^\s|&;()<>=])|<(?![<(=>])\s*[^\s|&;()<>=])")
_PIPE = re.compile(r"\|")


def _basename(argv0: str) -> str:
    return argv0.rsplit("/", 1)[-1]


#: Environment variables that can run code, inject libraries, or alter binary execution.
DANGEROUS_ENV_VARS = frozenset({
    "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT",
    "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH",
    "PAGER", "EDITOR", "VISUAL",
    "GIT_PAGER", "GIT_EDITOR", "GIT_SEQUENCE_EDITOR",
    "GIT_EXTERNAL_DIFF", "GIT_SSH", "GIT_SSH_COMMAND", "GIT_ASKPASS",
    "PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME",
    "NODE_OPTIONS", "RUBYOPT", "PERL5OPT", "PERL5LIB",
    "BASH_ENV", "ENV", "PROMPT_COMMAND",
})

#: Wrappers/prefixes stripped before binary dispatch (no bypass by prefix).
_WRAPPERS = frozenset({"env", "sudo", "command", "nohup", "time", "nice", "stdbuf"})


def _strip_wrapper_flags(wrapper: str, argv: list) -> list:
    """Consume known options for a specific wrapper until the command binary or end-of-options."""
    while argv:
        token = argv[0]
        if token == "--":
            argv = argv[1:]
            break
        if not token.startswith("-"):
            break

        if wrapper == "env":
            if token in ("-i", "--ignore-environment", "-0", "--null", "-v", "--debug"):
                argv = argv[1:]
            elif token in ("-u", "--unset", "-C", "--chdir", "-S", "--split-string", "-a", "--argv0"):
                if len(argv) > 1:
                    argv = argv[2:]
                else:
                    argv = argv[1:]
            elif token.startswith(("--unset=", "--chdir=", "--split-string=", "--argv0=",
                                  "-u=", "-C=", "-S=", "-a=")):
                argv = argv[1:]
            elif re.fullmatch(r"-[uCSa].+", token):
                argv = argv[1:]
            else:
                break

        elif wrapper == "sudo":
            if token in ("--non-interactive", "--preserve-env", "--set-home", "--preserve-groups",
                         "--stdin", "--background", "--reset-timestamp", "--remove-timestamp",
                         "--shell", "--login", "--validate", "--list", "--edit", "--version", "--help"):
                argv = argv[1:]
            elif token.startswith("--preserve-env="):
                argv = argv[1:]
            elif re.fullmatch(r"-[nEHPSbkKsivleVh]+", token):
                argv = argv[1:]
            elif token in ("-u", "--user", "-g", "--group", "-h", "--host", "-p", "--prompt",
                           "-C", "--close-from", "-R", "--chroot", "-D", "--chdir",
                           "-T", "--command-timeout", "-U", "--other-user"):
                if len(argv) > 1:
                    argv = argv[2:]
                else:
                    argv = argv[1:]
            elif token.startswith(("--user=", "--group=", "--host=", "--prompt=",
                                  "--close-from=", "--chroot=", "--chdir=",
                                  "--command-timeout=", "--other-user=",
                                  "-u=", "-g=", "-h=", "-p=", "-C=", "-R=", "-D=", "-T=", "-U=")):
                argv = argv[1:]
            elif re.fullmatch(r"-[ughpCRDTU].+", token):
                argv = argv[1:]
            else:
                break

        elif wrapper == "nice":
            if token in ("-n", "--adjustment"):
                if len(argv) > 1:
                    argv = argv[2:]
                else:
                    argv = argv[1:]
            elif token.startswith("--adjustment="):
                argv = argv[1:]
            elif re.fullmatch(r"-n[-+]?\d+", token):
                argv = argv[1:]
            elif re.fullmatch(r"[-+][0-9]+", token):
                argv = argv[1:]
            elif token in ("--help", "--version"):
                argv = argv[1:]
            else:
                break

        elif wrapper == "stdbuf":
            if token in ("-i", "-o", "-e", "--input", "--output", "--error"):
                if len(argv) > 1:
                    argv = argv[2:]
                else:
                    argv = argv[1:]
            elif token.startswith(("--input=", "--output=", "--error=")):
                argv = argv[1:]
            elif re.fullmatch(r"-[ioe].+", token):
                argv = argv[1:]
            elif token in ("--help", "--version"):
                argv = argv[1:]
            else:
                break

        elif wrapper == "time":
            if token in ("-f", "--format", "-o", "--output"):
                if len(argv) > 1:
                    argv = argv[2:]
                else:
                    argv = argv[1:]
            elif token.startswith(("--format=", "--output=", "-f=", "-o=")):
                argv = argv[1:]
            elif re.fullmatch(r"-[fo].+", token):
                argv = argv[1:]
            elif re.fullmatch(r"-[pva]+", token) or token in ("--portability", "--verbose", "--append", "--help", "--version"):
                argv = argv[1:]
            else:
                break

        elif wrapper == "command":
            if re.fullmatch(r"-[pvV]+", token) or token in ("--help", "--version"):
                argv = argv[1:]
            else:
                break

        elif wrapper == "nohup":
            if token in ("--help", "--version"):
                argv = argv[1:]
            else:
                break

        else:
            break

    return argv


def _strip_wrappers(argv: list, dangerous: list[str] | None = None, info: dict | None = None) -> list:
    """Remove env assignments and wrapper commands so `env rm x` etc. dispatch on the real binary."""
    argv = list(argv)
    wrapper_seen = False
    while argv:
        head = argv[0]
        if "=" in head and not head.startswith("-") and "/" not in head.split("=")[0]:
            name = head.split("=", 1)[0]
            if name in DANGEROUS_ENV_VARS or name.upper() in DANGEROUS_ENV_VARS:
                if dangerous is not None:
                    dangerous.append(name)
            argv = argv[1:]
            continue
        w = _basename(head)
        if w in _WRAPPERS:
            wrapper_seen = True
            argv = argv[1:]
            argv = _strip_wrapper_flags(w, argv)
            while argv and "=" in argv[0] and not argv[0].startswith("-"):
                name = argv[0].split("=", 1)[0]
                if name in DANGEROUS_ENV_VARS or name.upper() in DANGEROUS_ENV_VARS:
                    if dangerous is not None:
                        dangerous.append(name)
                argv = argv[1:]
            continue
        break
    if info is not None:
        info["wrapper_seen"] = wrapper_seen
        if wrapper_seen and argv and argv[0].startswith("-"):
            info["unknown_wrapper_flag"] = argv[0]
    return argv


def _strip_git_globals(rest: list) -> tuple[list, list[str]]:
    """Remove git global flags before subcommand dispatch; return (rest, dir_operands)."""
    operands: list[str] = []
    out: list[str] = []
    index = 0
    while index < len(rest):
        token = rest[index]
        if token == "-C" and index + 1 < len(rest):
            operands.append(rest[index + 1])
            index += 2
        elif token.startswith("--git-dir=") or token.startswith("--work-tree="):
            operands.append(token.split("=", 1)[1])
            index += 1
        elif token in ("--git-dir", "--work-tree") and index + 1 < len(rest):
            operands.append(rest[index + 1])
            index += 2
        elif token == "-c" and index + 1 < len(rest):
            index += 2
        else:
            out.append(token)
            # First non-flag token is the subcommand; the rest are subcommand args.
            if not token.startswith("-"):
                out.extend(rest[index + 1:])
                break
            index += 1
    return out, operands


#: sed one-letter commands that only transform or print the pattern space.
_SED_SAFE_COMMANDS = frozenset("abcdDgGhHilnNpPqQrRTvxyzFbt=:#")

#: One sed address: line number, last line, /regex/ or \cregexc.
_SED_ADDR_ONE = re.compile(r"""\s*(?:
      \d+                     # line number
    | \$                      # last line
    | /(?:\\.|[^/\\])*/?      # /regex/ (tolerate unterminated)
    | \\(.)(?:\\.|(?!\1).)*\1?  # \cregexc (tolerate unterminated)
    )\s*""", re.VERBOSE)

#: s<delim>pattern<delim>replacement<delim>flags, with escaped delimiters.
_SED_SUBST = re.compile(r"s(.)(?:\\\1|(?!\1).)*\1(?:\\\1|(?!\1).)*\1\s*([A-Za-z0-9]*)")


def _strip_sed_address(text: str) -> str:
    """Remove a leading sed address or address range (at most addr[,addr])."""
    pos = 0
    for _ in range(2):
        match = _SED_ADDR_ONE.match(text, pos)
        if not match:
            break
        pos = match.end()
        if text[pos:].lstrip()[:1] == ",":
            pos = text.index(",", pos) + 1
        else:
            break
    return text[pos:]


def _sed_script_mutates(script: str) -> bool:
    """True if a sed program writes files (w/W commands or flags) or runs code (e)."""
    for chunk in re.split(r"[;\n]", script):
        text = chunk.strip()
        if not text or text.startswith("#"):
            continue
        text = _strip_sed_address(text).lstrip("{ \t}")
        if text[:1] == "!":
            text = text[1:].lstrip()
        if not text or text[0] in "{}":
            continue
        cmd = text[0]
        if cmd in ("w", "W", "e"):
            return True
        if cmd == "s":
            match = _SED_SUBST.match(text)
            if match is None:
                return True  # unparsable substitute fails closed
            if any(flag in ("w", "W", "e") for flag in match.group(2)):
                return True
        elif cmd not in _SED_SAFE_COMMANDS:
            return True  # unknown command letter fails closed
    return False


def _sed_scripts(rest: list) -> list | None:
    """Inline sed programs from -e/positional operands.

    Returns None when the program comes from -f (a file: uninspectable).
    """
    exprs: list = []
    positionals: list = []
    index = 0
    while index < len(rest):
        arg = rest[index]
        if arg in ("-e", "--expression"):
            if index + 1 >= len(rest):
                return None  # dangling -e: uninspectable
            exprs.append(rest[index + 1])
            index += 2
        elif arg.startswith("--expression="):
            exprs.append(arg.split("=", 1)[1])
            index += 1
        elif arg in ("-f", "--file") or arg.startswith("--file="):
            return None
        elif arg == "--":
            positionals.extend(rest[index + 1:])
            break
        elif arg == "--line-length":
            index += 2  # operand is a width, never a program
        elif arg.startswith("--"):
            index += 1
        elif arg.startswith("-") and len(arg) > 1:
            consumed = 1
            for pos, char in enumerate(arg[1:], start=1):
                if char == "e":
                    if pos + 1 < len(arg):
                        exprs.append(arg[pos + 1:])
                    elif index + 1 < len(rest):
                        exprs.append(rest[index + 1])
                        consumed = 2
                    else:
                        return None  # dangling -e: uninspectable
                    break
                if char == "f":
                    return None
                if char == "l":
                    if pos + 1 < len(arg):
                        break  # -l70: width glued on, nothing follows
                    consumed = 2  # -l 70: skip the width operand
                    break
            index += consumed
        else:
            positionals.append(arg)
            index += 1
    if not exprs and positionals:
        exprs.append(positionals[0])
    return exprs


def _is_sed_inplace(arg: str) -> bool:
    """True if arg is an in-place editing flag (-i, -i.bak, -ni, --in-place, --in-place=SUFFIX)."""
    if arg == "--in-place" or arg.startswith("--in-place="):
        return True
    if arg.startswith("-") and not arg.startswith("--") and len(arg) > 1:
        for char in arg[1:]:
            if char in ("e", "f"):
                break
            if char == "i":
                return True
    return False


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
    if binary == "sed" and any(_is_sed_inplace(arg) for arg in rest):
        files = []
        has_expr = False
        idx = 0
        while idx < len(rest):
            arg = rest[idx]
            if arg == "--":
                files.extend(rest[idx + 1:])
                break
            elif arg in ("-e", "-f", "--expression", "--file", "-l", "--line-length"):
                if arg in ("-e", "-f", "--expression", "--file"):
                    has_expr = True
                idx += 2
            elif arg.startswith(("-e", "-f", "--expression=", "--file=")):
                has_expr = True
                idx += 1
            elif arg.startswith("-"):
                idx += 1
            else:
                files.append(arg)
                idx += 1
        return files if has_expr else files[1:]
    return []


def classify_shell_segment(segment: str, _depth: int = 0) -> dict:
    """Classify one pipeline segment (no top-level | ; &)."""
    try:
        argv = shlex.split(segment, posix=True)
    except ValueError:
        return {"mutation": "mutation", "reason": "unparsable shell segment fails closed"}
    if not argv:
        return {"mutation": "none", "reason": "empty segment"}
    dangerous_vars: list[str] = []
    info: dict = {}
    argv = _strip_wrappers(argv, dangerous=dangerous_vars, info=info)
    if not argv:
        return {"mutation": "mutation", "reason": "wrapper-only segment fails closed"}
    if info.get("unknown_wrapper_flag"):
        flag = info["unknown_wrapper_flag"]
        return {"mutation": "destructive", "executable": flag, "argv": argv,
                "reason": f"unrecognized wrapper flag {flag!r} fails closed to destructive"}
    result = _classify_shell_segment_binary(argv, segment, _depth=_depth)
    if dangerous_vars and LEVELS.index(result["mutation"]) < LEVELS.index("mutation"):
        result["mutation"] = "mutation"
        var_names = ", ".join(dict.fromkeys(dangerous_vars))
        existing = result.get("reason", "")
        suffix = f"; {existing}" if existing else ""
        result["reason"] = f"dangerous environment variable {var_names} can execute code or inject libraries{suffix}"
    return result


def _classify_shell_segment_binary(argv: list, segment: str, _depth: int = 0) -> dict:
    binary = _basename(argv[0])
    rest = argv[1:]

    if binary in DESTRUCTIVE_BINARIES:
        return {"mutation": "destructive", "executable": binary, "argv": argv,
                "reason": f"{binary} is never read-only"}
    if binary == "git":
        _i = 0
        while _i < len(rest):
            token = rest[_i]
            if token == "-c" and _i + 1 < len(rest):
                if any(k in rest[_i + 1].split("=", 1)[0].lower() for k in _GIT_EXEC_CONFIG):
                    return {"mutation": "mutation", "executable": "git", "argv": argv,
                            "reason": "git -c sets a config key that can run a program"}
                _i += 2
            elif token in ("-C", "--git-dir", "--work-tree") and _i + 1 < len(rest):
                _i += 2
            elif token.startswith("-"):
                _i += 1
            else:
                break
        rest, _git_dirs = _strip_git_globals(rest)
        sub = rest[0] if rest else ""
        if sub in DESTRUCTIVE_GIT:
            return {"mutation": "destructive", "executable": "git", "argv": argv,
                    "reason": f"git {sub} destroys or overwrites state"}
        if sub == "branch":
            args = rest[1:]
            flags = set(args)
            if flags & {"-d", "-D", "--delete", "-m", "-M", "--move", "-c", "--copy",
                        "-C", "-f", "--force"}:
                return {"mutation": "destructive", "executable": "git", "argv": argv,
                        "reason": "git branch delete/rename/force changes or destroys refs"}
            list_mode = any(a in {"-l", "--list", "--show-current"}
                            or a.split("=", 1)[0] in {"--contains", "--no-contains", "--merged",
                                                      "--no-merged", "--points-at"}
                            for a in args)
            writes_config = any(a in {"-u", "-t", "--track", "--no-track", "--unset-upstream",
                                      "--edit-description"}
                                or a.startswith(("--set-upstream-to", "--track=")) for a in args)
            positional = [a for a in args if not a.startswith("-")]
            if writes_config or (positional and not list_mode):
                return {"mutation": "mutation", "executable": "git", "argv": argv,
                        "reason": "git branch creates a branch or edits branch config"}
            return {"mutation": "none", "executable": "git", "argv": argv,
                    "reason": "git branch is a read-only query"}
        if sub == "stash":
            verb = rest[1] if len(rest) > 1 else "push"
            if verb in ("drop", "clear"):
                return {"mutation": "destructive", "executable": "git", "argv": argv,
                        "reason": f"git stash {verb} deletes stashes"}
            if verb == "list":
                return {"mutation": "none", "executable": "git", "argv": argv,
                        "reason": "git stash list is a read-only query"}
            return {"mutation": "mutation", "executable": "git", "argv": argv,
                    "reason": f"git stash {verb} mutates repository state"}
        if sub == "worktree":
            verb = rest[1] if len(rest) > 1 else ""
            if verb == "remove":
                return {"mutation": "destructive", "executable": "git", "argv": argv,
                        "reason": "git worktree remove deletes a worktree"}
            if verb == "list":
                return {"mutation": "none", "executable": "git", "argv": argv,
                        "reason": "git worktree list is a read-only query"}
            return {"mutation": "mutation", "executable": "git", "argv": argv,
                    "reason": f"git worktree {verb} mutates worktrees"}
        if sub in {"add", "commit", "push", "merge", "rebase"}:
            return {"mutation": "mutation", "executable": "git", "argv": argv,
                    "reason": f"git {sub} mutates repository state"}
        if sub in {"diff", "show", "log"} and any(
                a == "--output" or a.startswith("--output=") or a == "--ext-diff"
                for a in rest[1:]):
            return {"mutation": "mutation", "executable": "git", "argv": argv,
                    "reason": f"git {sub} --output writes a file; --ext-diff runs a program"}
        if sub in READ_GIT:
            return {"mutation": "none", "executable": "git", "argv": argv,
                    "reason": f"git {sub} is a read-only query"}
        return {"mutation": "mutation", "executable": "git", "argv": argv,
                "reason": "unknown git subcommand fails closed"}
    if binary == "xargs" and _depth < 2:
        tail = [a for a in rest if not a.startswith("-") and a != "--"]
        if tail:
            # Classify the trailing command with the same machinery.
            inner_result = classify_shell_segment(" ".join(tail), _depth=_depth + 1)
            level = inner_result["mutation"]
            if LEVELS.index(level) < LEVELS.index("mutation"):
                level = "mutation"
            return {"mutation": level, "executable": binary, "argv": argv,
                    "reason": f"xargs executes: {inner_result.get('reason', '')}"}
        return {"mutation": "mutation", "executable": binary, "argv": argv,
                "reason": "xargs executes commands per input line"}
    if binary in {"rm", "mv"}:
        return {"mutation": "destructive", "executable": binary, "argv": argv,
                "reason": f"{binary} deletes or moves state"}
    if binary in {"cp", "touch", "mkdir", "ln", "sed", "patch", "tar", "unzip", "zip", "install",
                   "ed", "ex", "vi", "vim", "nano", "emacs"}:
        if binary == "sed" and not any(_is_sed_inplace(arg) for arg in rest):
            scripts = _sed_scripts(rest)
            if scripts is not None and not any(_sed_script_mutates(s) for s in scripts):
                return {"mutation": "none", "executable": binary, "argv": argv,
                        "reason": "sed without -i only filters text"}
            if scripts is None:
                return {"mutation": "mutation", "executable": binary, "argv": argv,
                        "reason": "sed -f reads its program from a file; fails closed"}
            return {"mutation": "mutation", "executable": binary, "argv": argv,
                    "reason": "sed script writes files (w) or executes commands (e)"}
        return {"mutation": "mutation", "executable": binary, "argv": argv,
                "reason": f"{binary} writes files"}
    if binary in {"python", "python3", "node", "deno", "ruby", "php", "perl", "bash", "sh"}:
        if rest[:1] in (["-c"], ["-e"], ["--eval"]):
            payload = rest[1] if len(rest) > 1 else ""
            inner_level = "mutation"
            inner_reason = f"{binary} {rest[0]} executes arbitrary code"
            if payload and _depth < 2:
                try:
                    inner = classify_shell(payload, _depth=_depth + 1)
                    if LEVELS.index(inner["mutation"]) > LEVELS.index(inner_level):
                        inner_level = inner["mutation"]
                        inner_reason += f" (inner: {inner['reason']})"
                except Exception:
                    pass
            return {"mutation": inner_level, "executable": binary, "argv": argv,
                    "reason": inner_reason}
        for flag in ("-m",):
            if rest[:1] == [flag]:
                return {"mutation": "mutation", "executable": binary, "argv": argv,
                        "reason": f"{binary} {flag} executes a module"}
        if any(arg.endswith(".py") or arg.endswith(".js") for arg in rest):
            return {"mutation": "mutation", "executable": binary, "argv": argv,
                    "reason": f"{binary} runs a script file"}
        if not rest or rest == ["-"]:
            return {"mutation": "mutation", "executable": binary, "argv": argv,
                    "reason": f"{binary} reads a script from stdin or starts a REPL"}
        if rest[:1] in (["--version"], ["-V"], ["-h"], ["--help"]):
            return {"mutation": "none", "executable": binary, "argv": argv,
                    "reason": f"{binary} version/flag query"}
        return {"mutation": "mutation", "executable": binary, "argv": argv,
                "reason": f"{binary} invocation fails closed (not a known read-only query)"}
    if binary in {"npm", "pip", "pip3", "yarn", "pnpm", "cargo", "go"}:
        verb = rest[0] if rest else ""
        if verb in {"install", "publish", "add", "remove", "uninstall", "test", "run"}:
            return {"mutation": "mutation", "executable": binary, "argv": argv,
                    "reason": f"{binary} {verb} changes state or executes project code"}
        if binary == "cargo" and verb in {"check", "c"}:
            # cargo check compiles and runs build.rs and proc macros, so it is
            # not read-only (it must agree with the "cargo check" CHECK_COMMANDS entry).
            return {"mutation": "mutation", "executable": binary, "argv": argv,
                    "reason": "cargo check executes build scripts and proc macros (side effects possible)"}
        if verb in {"", "ls", "list", "view", "show", "freeze", "check", "--version", "version"}:
            return {"mutation": "none", "executable": binary, "argv": argv,
                    "reason": f"{binary} {verb or 'query'} is read-only"}
        return {"mutation": "mutation", "executable": binary, "argv": argv,
                "reason": f"{binary} {verb} is not a known read-only verb; fails closed"}
    if binary == "find":
        if ("-delete" in rest or "-exec" in rest or "-execdir" in rest
                or "-ok" in rest or "-okdir" in rest or "-fls" in rest or "-fprint" in rest
                or any(a.startswith(("-exec", "-ok", "-fls", "-fprint", "-delete")) for a in rest)):
            return {"mutation": "destructive", "executable": binary, "argv": argv,
                    "reason": "find -delete/-exec acts on the tree"}
        return {"mutation": "none", "executable": binary, "argv": argv,
                "reason": "find query is read-only"}
    if binary == "echo":
        return {"mutation": "none", "executable": binary, "argv": argv,
                "reason": "echo without redirection only writes stdout"}
    if binary == "rg" and any(a == "--pre" or a.startswith("--pre=") for a in rest):
        return {"mutation": "mutation", "executable": binary, "argv": argv,
                "reason": "rg --pre runs a program on every file"}
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


def classify_shell(command: str, _depth: int = 0) -> dict:
    """Classify a full shell command line. Worst segment wins."""
    text = command.strip()
    if not text:
        return {"mutation": "none", "reason": "empty command"}
    if _depth > 2:
        return {"mutation": "mutation", "reason": "nested shell depth fails closed"}
    segments = [seg for seg in re.split(r"[;&|\r\n]+", text) if seg.strip()]
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
        for match in re.finditer(r"(?:>>?|&>>?|<)\s*([^\s;&|]+)", text):
            target = match.group(1)
            if not target.startswith("&") and target not in paths:
                paths.append(target)
    for segment in segments:
        operand_paths = _operand_paths(segment)
        for operand in operand_paths:
            if operand not in paths:
                paths.append(operand)
        try:
            seg_argv = _strip_wrappers(shlex.split(segment, posix=True))
        except ValueError:
            seg_argv = []
        if seg_argv and _basename(seg_argv[0]) == "git":
            _, git_dirs = _strip_git_globals(seg_argv[1:])
            for operand in git_dirs:
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


# ---------------------------------------------------------------------------
# Path identity: canonicalize at record, fold at compare.
# ---------------------------------------------------------------------------

#: APFS/HFS+ treat NFC and NFD names as the same file; ext4 and NTFS do not.
UNICODE_INSENSITIVE_FS = sys.platform == "darwin"


def canonical_path(raw: str, roots: list[Path] | None = None, *,
                   windows: bool | None = None) -> Path:
    """Record-time path identity: absolute, lexical-normalized, and symlink-aware.

    Relative paths join the first workspace root (cwd when none). ``.`` and
    ``..`` are folded lexically so the original case and Unicode remain visible
    to scope checks, while symlinks still resolve to their target. A plain path
    on a case-insensitive volume should not be silently rewritten to a different
    case just because the filesystem folds it; :func:`path_key` does the
    compare-time folding instead.
    """
    text = str(raw)
    if os.name == "nt" if windows is None else windows:
        text = text.replace("\\", "/")
    path = Path(text)
    if not path.is_absolute():
        path = (roots[0] if roots else Path.cwd()) / path

    lexical = Path(os.path.abspath(os.path.normpath(str(path))))
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        return lexical.resolve(strict=False)
    return lexical


@lru_cache(maxsize=None)
def case_insensitive_fs(path: Path) -> bool:
    """Probe whether the volume holding ``path`` folds case.

    Uses the nearest existing ancestor whose name has letters; falls back
    to the platform default (macOS/Windows fold) when nothing is probeable.
    """
    for probe in (path, *path.parents):
        swapped = probe.name.swapcase()
        if swapped == probe.name:
            continue
        try:
            if probe.exists():
                return os.path.samefile(probe, probe.with_name(swapped))
        except OSError:
            return False
    return sys.platform in ("darwin", "win32")


def path_key(path: Path, *, case_insensitive: bool,
             unicode_insensitive: bool = UNICODE_INSENSITIVE_FS) -> str:
    """Compare-time identity of a :func:`canonical_path` result."""
    text = str(path)
    if unicode_insensitive:
        text = unicodedata.normalize("NFC", text)
    if case_insensitive:
        text = text.lower()
    return text


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
