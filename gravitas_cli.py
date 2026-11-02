"""Command line interface for Gravitas runtime operations."""
from __future__ import annotations

import argparse
import json
import hashlib
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent


def installed_assets_root() -> Path | None:
    """Location of runtime assets shipped inside the wheel (sys.prefix/share).

    The wheel lays files out under share/gravitas/ mirroring the repository
    root (plugins/..., skills/...), so the rest of the CLI works unchanged.
    """
    candidate = Path(sys.prefix) / "share" / "gravitas" / "plugins" / "gravitas-antigravity"
    if (candidate / "scripts").is_dir():
        return candidate.parents[1]  # share/gravitas/ mirrors the repo layout root
    return None


def runtime_root() -> Path:
    """Resolve runtime assets: checkout first, installed distribution next."""
    checkout = Path.cwd()
    if (checkout / "plugins" / "gravitas-antigravity" / "scripts").is_dir():
        return checkout
    if (MODULE_ROOT / "plugins" / "gravitas-antigravity" / "scripts").is_dir():
        return MODULE_ROOT
    installed = installed_assets_root()
    if installed is not None:
        return installed
    return MODULE_ROOT


def runtime_mode() -> str:
    checkout = Path.cwd()
    if (checkout / "plugins" / "gravitas-antigravity" / "scripts").is_dir():
        return "checkout(cwd)"
    if (MODULE_ROOT / "plugins" / "gravitas-antigravity" / "scripts").is_dir():
        return "checkout(module)"
    if installed_assets_root() is not None:
        return "installed"
    return "unresolved"


ROOT = runtime_root()
SCRIPTS = ROOT / "plugins" / "gravitas-antigravity" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def sessions(root: Path) -> list[Path]:
    directory = root / ".gravitas" / "sessions"
    return sorted((path for path in directory.iterdir() if path.is_dir()), key=lambda path: path.stat().st_mtime, reverse=True) if directory.exists() else []


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check the effective runtime plus the other two supported contexts.

    Modes: repository checkout (cwd or module dir), installed distribution
    (sys.prefix/share), or a configured user project (cwd with .gravitas/).
    Each scope is reported separately so failures point at the right layer.
    """
    native = ROOT / "plugins" / "gravitas-antigravity"
    checks = {
        "mode": runtime_mode(),
        "runtime_root": str(ROOT),
        "skill": (ROOT / "skills/gravitas/SKILL.md").is_file(),
        "highstakes_skill": (ROOT / "skills/gravitas-highstakes/SKILL.md").is_file(),
        "plugin_manifest": (native / "plugin.json").is_file(),
        "hooks": (native / "hooks.json").is_file(),
        "validator_runner": (SCRIPTS / "validator_runner.py").is_file(),
        "pre_tool_hook": (SCRIPTS / "pre_tool.py").is_file(),
        "post_tool_hook": (SCRIPTS / "post_tool.py").is_file(),
        "post_invocation_hook": (SCRIPTS / "post_invocation.py").is_file(),
        "stop_gate_hook": (SCRIPTS / "stop_gate.py").is_file(),
        "evidence_chain": (SCRIPTS / "evidence_chain.py").is_file(),
        "project_session_store": (Path.cwd() / ".gravitas" / "sessions").is_dir(),
        "adapters": (ROOT / "adapters" / "opencode" / "contract-template.json").is_file(),
        "adapter_permissions": (ROOT / "adapters" / "opencode" / "permissions" / "balanced.json").is_file(),
        "project_opencode_contract": (Path.cwd() / ".gravitas" / "opencode-contract.json").is_file(),
        "project_opencode_skill": (Path.cwd() / ".agents" / "skills" / "gravitas" / "SKILL.md").is_file(),
    }
    print(json.dumps(checks, indent=2))
    required = ["skill", "highstakes_skill", "plugin_manifest", "hooks", "validator_runner",
                "pre_tool_hook", "post_tool_hook", "post_invocation_hook",
                "stop_gate_hook", "evidence_chain"]
    return 0 if all(checks[key] for key in required) else 1


def cmd_bench(args: argparse.Namespace) -> int:
    """Delegate to the GravitasBench CLI (requires a repository checkout)."""
    bench_cli = ROOT / "benchmarks" / "cli.py"
    if not bench_cli.is_file():
        print(json.dumps({"error": "benchmarks/cli.py not found; `gravitas bench` requires a Gravitas repository checkout"}))
        return 1
    import importlib.util
    spec = importlib.util.spec_from_file_location("gravitas_bench_cli", bench_cli)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main(list(args.bench_args))


def cmd_status(args: argparse.Namespace) -> int:
    found = sessions(Path.cwd())
    output = []
    for session in found:
        contract = session / "contract.json"
        state = session / "state.json"
        output.append({"session": str(session), "contract": contract.exists(), "state": json.loads(state.read_text()) if state.exists() else None})
    print(json.dumps(output, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    target = Path(args.session_dir) / "evidence.jsonl"
    try:
        from evidence_chain import backfill_anchors, verify_with_anchor
    except ModuleNotFoundError:
        print(json.dumps({"valid": False, "reason": f"runtime assets not found under {ROOT}; reinstall gravitas or run from a checkout", "ledger": str(target)}))
        return 1
    if args.backfill_anchors:
        ok, detail = backfill_anchors(Path(args.session_dir))
        if not ok:
            print(json.dumps({"valid": False, "backfilled": False, "reason": detail, "ledger": str(target)}))
            return 1
        valid, reason = verify_with_anchor(Path(args.session_dir))
        print(json.dumps({"valid": valid, "backfilled": True, "reason": reason, "ledger": str(target)}))
        return 0 if valid else 1
    valid, reason = verify_with_anchor(Path(args.session_dir))
    print(json.dumps({"valid": valid, "reason": reason, "ledger": str(target)}))
    return 0 if valid else 1


def cmd_gc(args: argparse.Namespace) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.older_than_days)
    removed = []
    for session in sessions(Path.cwd()):
        modified = datetime.fromtimestamp(session.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            if args.apply:
                shutil.rmtree(session)
            removed.append(str(session))
    print(json.dumps({"would_remove" if not args.apply else "removed": removed}))
    return 0


def cmd_validator(args: argparse.Namespace) -> int:
    command = [sys.executable, str(SCRIPTS / "validator_runner.py"), "--session-dir", args.session_dir, "--validator-id", args.validator_id]
    for criterion in args.criterion_id:
        command.extend(["--criterion-id", criterion])
    user_command = args.command[1:] if args.command[:1] == ["--"] else args.command
    command.extend(["--", *user_command])
    return subprocess.run(command, check=False).returncode


def cmd_decide(args: argparse.Namespace) -> int:
    """Emit a machine-readable planning-policy record from signals JSON."""
    try:
        from gravitas_policy import decide
    except ModuleNotFoundError:
        print(json.dumps({"error": f"runtime assets not found under {ROOT}; reinstall gravitas or run from a checkout"}))
        return 1
    if args.signals:
        try:
            signals = json.loads(args.signals)
        except json.JSONDecodeError as error:
            print(json.dumps({"error": f"signals is not valid JSON: {error}"}))
            return 1
    else:
        signals = {}
    if not isinstance(signals, dict):
        print(json.dumps({"error": "signals must be a JSON object"}))
        return 1
    print(json.dumps(decide(signals), indent=2))
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    try:
        from gravitas_context import summarize_session
    except ModuleNotFoundError:
        print(json.dumps({"error": f"runtime assets not found under {ROOT}; reinstall gravitas or run from a checkout"}))
        return 1
    session_dir = Path(args.session_dir)
    if not (session_dir / "contract.json").exists() and not (session_dir / "state.json").exists():
        print(json.dumps({"error": f"not a Gravitas session directory: {session_dir}"}))
        return 1
    print(json.dumps(summarize_session(session_dir), indent=2))
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    try:
        from impact_graph import verification_context
    except ModuleNotFoundError:
        print(json.dumps({"error": f"runtime assets not found under {ROOT}; reinstall gravitas or run from a checkout"}))
        return 1
    print(json.dumps(verification_context(Path(args.root), args.changed, args.depth), indent=2))
    return 0


def cmd_validators(args: argparse.Namespace) -> int:
    try:
        from gravitas_verify import discover_validators, escalation_plan
        from gravitas_repo import context_for, get_index
    except ModuleNotFoundError:
        print(json.dumps({"error": f"runtime assets not found under {ROOT}; reinstall gravitas or run from a checkout"}))
        return 1
    root = Path(args.root)
    catalog = discover_validators(root)
    related: dict = {}
    if args.changed:
        try:
            index = get_index(root)
            for target in args.changed:
                context = context_for(index, [target], "dependency")
                related[target] = [p for p in context["files"] if p != target]
        except OSError:
            pass
    print(json.dumps({
        "catalog": catalog,
        "plan": escalation_plan(
            catalog, verification_depth=args.depth, changed=args.changed,
            related=related, failure_evidence=args.failure_evidence,
            release_context=args.release),
    }, indent=2))
    return 0


def cmd_repro(args: argparse.Namespace) -> int:
    command = [sys.executable, str(SCRIPTS / "repro_runner.py"),
               "--session-dir", args.session_dir, "--criterion-id", args.criterion_id,
               "--phase", args.phase, "--cwd", args.cwd]
    if args.reproducer_id:
        command.extend(["--reproducer-id", args.reproducer_id])
    if args.unreproducible:
        command.extend(["--unreproducible", "--reason", args.reason])
        return subprocess.run(command, check=False).returncode
    user_command = args.command[1:] if args.command[:1] == ["--"] else args.command
    command.extend(["--", *user_command])
    return subprocess.run(command, check=False).returncode


def cmd_resolve_failure(args: argparse.Namespace) -> int:
    """Mark a failed-approach fingerprint resolved after its cause is gone.

    Appends a resolution marker to failures.jsonl; pre_tool then stops
    banning that exact fingerprint. The original failure record is kept.
    """
    from datetime import datetime, timezone
    session_dir = Path(args.session_dir)
    if not session_dir.is_dir():
        print(json.dumps({"ok": False, "error": f"not a session directory: {session_dir}"}))
        return 1
    if not args.fingerprint or not args.reason:
        print(json.dumps({"ok": False, "error": "fingerprint and reason are both required"}))
        return 1
    failures_path = session_dir / "failures.jsonl"
    failures = []
    if failures_path.exists():
        for line in failures_path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                failures.append(entry)

    original = next((entry for entry in reversed(failures)
                     if entry.get("fingerprint") == args.fingerprint
                     and entry.get("resolved") is not True), None)
    if original is None:
        print(json.dumps({"ok": False, "error": "no unresolved failure matches that fingerprint"}))
        return 1

    input_summary = original.get("input_summary", {})
    target_files = list(args.file)
    if isinstance(input_summary, dict):
        for key in ("TargetFile", "target_file", "filePath", "path", "AbsolutePath"):
            value = input_summary.get(key)
            if isinstance(value, str) and value:
                target_files.append(value)
    target_files = sorted(set(target_files))
    if not target_files:
        print(json.dumps({
            "ok": False,
            "error": "could not determine the failed action's target; supply --file before resolving",
        }))
        return 1

    criterion_ids = set(args.criterion_id)
    command = input_summary.get("CommandLine", input_summary.get("command", "")) if isinstance(input_summary, dict) else ""
    contract_path = session_dir / "contract.json"
    if contract_path.exists():
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            contract = {}
        if isinstance(contract, dict):
            declared_criteria = {
                item.get("id") for item in contract.get("acceptance_criteria", [])
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            unknown_criteria = criterion_ids - declared_criteria
            if unknown_criteria:
                print(json.dumps({
                    "ok": False,
                    "error": "unknown criterion ID(s): " + ", ".join(sorted(unknown_criteria)),
                }))
                return 1
            validators = contract.get("validators", [])
            if not isinstance(validators, list):
                validators = []
            for validator in validators:
                declared_command = validator.get("command") if isinstance(validator, dict) else None
                if (isinstance(command, str)
                        and isinstance(declared_command, list)
                        and all(isinstance(part, str) for part in declared_command)
                        and command.strip() in (
                            shlex.join(declared_command),
                            subprocess.list2cmdline(declared_command),
                        )):
                    criterion_ids.update(
                        identifier for identifier in validator.get("criterion_ids", [])
                        if isinstance(identifier, str)
                    )
            undeclared = criterion_ids - declared_criteria
            if undeclared:
                print(json.dumps({
                    "ok": False,
                    "error": "validator references unknown criterion ID(s): "
                    + ", ".join(sorted(undeclared)),
                }))
                return 1

    resolved_at = datetime.now(timezone.utc).isoformat()
    resolution_id = hashlib.sha256(
        f"{args.fingerprint}\0{resolved_at}\0{args.reason}".encode("utf-8")
    ).hexdigest()[:16]
    marker = {
        "fingerprint": args.fingerprint,
        "resolved": True,
        "resolution_id": resolution_id,
        "reason": args.reason,
        "timestamp": resolved_at,
        "required_reads": target_files,
        "criterion_ids": sorted(criterion_ids),
    }
    # Ledger-first ordering: the anchored evidence record must exist before
    # its failure-log marker. If anchoring the record fails, no marker is
    # written, so verification can never see an orphan "resolution metadata
    # is not anchored" deficit.
    try:
        from evidence_chain import append_evidence
        append_evidence(session_dir, {
            "source": "failure_resolution",
            "fingerprint": args.fingerprint,
            "resolution_id": resolution_id,
            "required_reads": target_files,
            "criterion_ids": sorted(criterion_ids),
            "reason": args.reason,
            "timestamp": resolved_at,
        })
    except (ModuleNotFoundError, OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": f"resolution marker could not be anchored: {error}"}))
        return 1
    with failures_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(marker) + "\n")
    print(json.dumps({"ok": True, "fingerprint": args.fingerprint,
                      "resolution_id": resolution_id,
                      "required_reads": target_files,
                      "criterion_ids": sorted(criterion_ids)}))
    return 0


def cmd_edge_cases(args: argparse.Namespace) -> int:
    try:
        from gravitas_verify import expand_cases
    except ModuleNotFoundError:
        print(json.dumps({"error": f"runtime assets not found under {ROOT}; reinstall gravitas or run from a checkout"}))
        return 1
    try:
        seeds = json.loads(args.seeds)
    except json.JSONDecodeError as error:
        print(json.dumps({"error": f"seeds is not valid JSON: {error}"}))
        return 1
    if not isinstance(seeds, list):
        print(json.dumps({"error": "seeds must be a JSON array"}))
        return 1
    print(json.dumps(expand_cases(seeds), indent=2))
    return 0


OPENCODE_TOOL_MAP = {
    "read": ("view_file", lambda a: {"AbsolutePath": a.get("filePath", a.get("path", ""))}),
    "edit": ("write_to_file", lambda a: {"TargetFile": a.get("filePath", a.get("path", ""))}),
    "write": ("write_to_file", lambda a: {"TargetFile": a.get("filePath", a.get("path", ""))}),
    "patch": ("replace_file_content", lambda a: {"target_file": a.get("filePath", a.get("path", ""))}),
    "bash": ("run_command", lambda a: {"CommandLine": a.get("command", "")}),
    "grep": ("grep_search", lambda a: dict(a)),
    "glob": ("find_by_name", lambda a: dict(a)),
    "list": ("list_dir", lambda a: dict(a)),
}


def _opencode_tool(tool: str, args: dict) -> tuple[str, dict]:
    mapped = OPENCODE_TOOL_MAP.get(tool)
    if mapped is None:
        return tool, args if isinstance(args, dict) else {}
    name, convert = mapped
    return name, convert(args if isinstance(args, dict) else {})


def _load_opencode_reads(contract_path: Path, session_id: str) -> set:
    """Load recorded OpenCode reads for read-before-write enforcement.

    The OpenCode shim appends ``{session, file, source}`` rows to
    ``.gravitas/opencode-reads.jsonl`` (cwd first, contract dir fallback).
    Rows from other sessions never satisfy this session's read check
    (exact session match; empty-session rows only match session-less
    checks). Corrupt lines are skipped; a missing file means no reads.
    """
    candidates = [
        Path.cwd() / ".gravitas" / "opencode-reads.jsonl",
        contract_path.parent / "opencode-reads.jsonl",
    ]
    reads: set = set()
    seen: set = set()
    for candidate in candidates:
        if str(candidate) in seen:
            continue
        seen.add(str(candidate))
        try:
            if not candidate.exists():
                continue
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict) or not row.get("file"):
                    continue
                if row.get("session") != session_id:
                    continue
                reads.add(str(row["file"]))
        except OSError:
            continue
    return reads


def opencode_session_evidence(root: Path, session_id: str) -> list[dict]:
    """Load completion and validator evidence without crossing OpenCode sessions."""
    if not session_id:
        return []
    from gravitas_evidence import opencode_completion_writes

    safe_id = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    evidence_path = root / ".gravitas" / "sessions" / f"opencode-{safe_id}" / "evidence.jsonl"
    entries = []
    if evidence_path.exists():
        for line in evidence_path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                entries.append(entry)
    completions = opencode_completion_writes(
        root / ".gravitas" / "opencode-completions.jsonl", session_id
    )
    return entries + completions


def cmd_guard(args: argparse.Namespace) -> int:
    """One policy decision for a host envelope on stdin/--envelope.

    Policy states (reported as ``policy_state``):
    active (contract ok), unconfigured (contract file missing),
    degraded (contract corrupt/invalid or mode unknown), disabled (never
    emitted here; no disable flag exists). Mutating actions are denied
    fail-closed unless the contract is valid and permits them. Read-only
    actions may pass with a warning so diagnostics stay usable.
    """
    try:
        from gravitas_action import HostEnvelope, normalize, workspace_roots
        from gravitas_policy import action_fingerprint, evaluate_action
    except ModuleNotFoundError:
        print(json.dumps({"decision": "deny", "policy_state": "degraded",
                          "reason": f"runtime assets not found under {ROOT}; reinstall gravitas or run from a checkout"}))
        return 0
    raw = args.envelope or sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"decision": "deny", "policy_state": "active", "reason": "guard could not parse the envelope; denied fail-closed"}))
        return 0
    if not isinstance(data, dict) or not isinstance(data.get("tool"), str):
        print(json.dumps({"decision": "deny", "policy_state": "active", "reason": "guard envelope has no tool"}))
        return 0
    envelope = HostEnvelope(tool=data["tool"], args=data.get("args", {}),
                            conversation_id=data.get("conversation_id", ""),
                            workspace_roots=data.get("workspace_roots", []),
                            host=data.get("host", ""), event=data.get("event", "before_action"))
    if envelope.host == "opencode":
        # OpenCode tool vocabulary onto the normalized model. Unknown tools
        # stay unmapped: visible (kind "other"), allowed with a warning.
        envelope.tool, envelope.args = _opencode_tool(envelope.tool, envelope.args)
    if not isinstance(envelope.args, dict):
        print(json.dumps({"decision": "deny", "policy_state": "active",
                          "reason": "guard envelope args must be an object; denied fail-closed"}))
        return 0
    # Empty mutating payloads fail closed: an adapter that drops arguments
    # must never turn a write/shell into an allow.
    if envelope.tool in ("write_to_file", "replace_file_content",
                         "multi_replace_file_content", "run_command") and not envelope.args:
        print(json.dumps({"decision": "deny", "policy_state": "active",
                          "reason": f"mutating tool {envelope.tool} arrived with no arguments; denied fail-closed"}))
        return 0
    contract_path = Path(args.contract) if args.contract else Path.cwd() / ".gravitas" / "opencode-contract.json"
    policy_state = "active"
    contract_warning = ""
    try:
        contract = json.loads(contract_path.read_text()) if contract_path.exists() else None
    except json.JSONDecodeError as error:
        contract = None
        policy_state = "degraded"
        contract_warning = f"contract {contract_path} is not valid JSON ({error}); mutating actions denied"
    if contract is None and not contract_warning:
        policy_state = "unconfigured"
        contract_warning = (f"no contract at {contract_path}; mutating actions denied. "
                            "Run `gravitas init` to create one")
        contract = {}
    if contract is None:
        contract = {}
    elif not isinstance(contract, dict):
        policy_state = "degraded"
        contract_warning = f"contract {contract_path} is not an object; mutating actions denied"
        contract = {}
    from gravitas_policy import MODES, MODE_ALIASES, normalize_mode
    raw_mode = contract.get("mode", "implement")
    if raw_mode not in MODES and raw_mode not in MODE_ALIASES:
        policy_state = "degraded" if policy_state == "active" else policy_state
        contract_warning = (contract_warning + " " if contract_warning else "") + \
            f"unknown mode {raw_mode!r}; denied fail-closed. Valid modes: {sorted(MODES)}"
        print(json.dumps({"decision": "deny", "policy_state": policy_state,
                          "reason": contract_warning.strip()}))
        return 0
    action = normalize(envelope.tool, envelope.args)
    mutating = action.kind == "write" or action.mutation != "none"
    if policy_state in ("unconfigured", "degraded") and mutating:
        print(json.dumps({"decision": "deny", "policy_state": policy_state,
                          "reason": contract_warning or "contract unavailable; denied fail-closed"}))
        return 0
    session_id = str(data.get("conversation_id", "") or data.get("sessionID", "")
                     or data.get("session_id", ""))
    reads = _load_opencode_reads(contract_path, session_id) if envelope.host == "opencode" else set()
    decision, reason = evaluate_action(
        action, mode=normalize_mode(contract.get("mode", "implement")),
        allowed_scope=contract.get("allowed_write_scope", []), reads=reads,
        failed_fingerprints=set(), roots=workspace_roots(envelope),
        fingerprint=action_fingerprint(envelope.tool, envelope.args))
    out = {"decision": "deny" if decision == "force_ask" else decision,
           "policy_state": policy_state}
    if reason:
        out["reason"] = reason
    if envelope.host == "opencode" and envelope.conversation_id:
        from gravitas_evidence import criterion_states
        states = criterion_states(
            contract, opencode_session_evidence(Path.cwd(), envelope.conversation_id)
        )
        stale = sorted(
            identifier for identifier, info in states.items()
            if info.get("stale_owned", 0) > 0
        )
        if stale:
            out["stale_validator_criteria"] = stale
    if contract_warning and out["decision"] == "allow":
        out["warning"] = contract_warning
    if envelope.tool not in ("view_file", "grep_search", "find_by_name", "list_dir",
                             "read_url_content", "search_web", "write_to_file",
                             "replace_file_content", "multi_replace_file_content",
                             "run_command") and out["decision"] == "allow":
        out["warning"] = (out.get("warning", "") + " unknown tool; allowed as visible-only (kind=other)").strip()
    print(json.dumps(out))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Scaffold host configuration in a project directory."""
    root = Path(args.root).resolve()
    # Templates ship with the checkout and inside the wheel (share/gravitas).
    for candidate in (Path.cwd(), MODULE_ROOT, ROOT):
        if (candidate / "adapters" / "opencode" / "contract-template.json").exists():
            source_root = candidate
            break
    else:
        print(json.dumps({"ok": False, "error": "adapter templates not found; reinstall gravitas"}))
        return 1
    if args.host == "opencode":
        from gravitas_init import init_opencode
        result = init_opencode(root, profile=args.profile, source_root=source_root)
    elif args.host == "antigravity":
        from gravitas_init import init_antigravity
        result = init_antigravity(root, source_root=source_root)
    else:
        from gravitas_init import detect_hosts, init_antigravity, init_opencode
        hosts = detect_hosts(root) or ["opencode"]
        results = []
        for host in hosts:
            if host == "opencode":
                results.append(init_opencode(root, profile=args.profile, source_root=source_root))
            else:
                results.append(init_antigravity(root, source_root=source_root))
        result = {"ok": all(r.get("ok") for r in results), "hosts": hosts, "results": results}
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def cmd_explain(args: argparse.Namespace) -> int:
    """Render what a session is, what is proven, and what is next."""
    try:
        from gravitas_context import summarize_session
        from gravitas_evidence import evidence_deficit
    except ModuleNotFoundError:
        print(json.dumps({"error": f"runtime assets not found under {ROOT}"}))
        return 1
    session_dir = Path(args.session_dir)
    if not session_dir.is_dir():
        message = f"not a session directory: {session_dir}"
        print(json.dumps({"error": message}) if args.json else message)
        return 1
    summary = summarize_session(session_dir)
    contract_path = session_dir / "contract.json"
    try:
        contract = json.loads(contract_path.read_text()) if contract_path.exists() else {}
    except json.JSONDecodeError:
        contract = {}
    states = summary.get("acceptance_criteria", {})
    deficit = evidence_deficit(contract if isinstance(contract, dict) else {}, {
        key: {"statement": value.get("statement", key), "status": value.get("status", "PENDING"),
              "stale_owned": 0}
        for key, value in states.items()})
    if args.json:
        print(json.dumps({**summary, "deficit": deficit}, indent=2))
        return 0
    lines = [
        f"Session: {summary.get('session')}  (mode={summary.get('mode')}, phase={summary.get('phase')})",
        f"Objective: {summary.get('objective')}",
        "",
        "Acceptance criteria:",
    ]
    for identifier, info in states.items():
        lines.append(f"  [{info.get('status', 'PENDING')}] {identifier}: {info.get('statement', '')}")
    if deficit:
        lines.append("")
        lines.append("Evidence deficit (what to do next):")
        for item in deficit:
            lines.append(f"  - {item['criterion']} ({item['status']}): {item['needed']}")
    else:
        lines.append("")
        lines.append("No evidence deficit. Ready for the completion gate.")
    failed = summary.get("failed_approaches", [])
    if failed:
        lines.append("")
        lines.append(f"Failed approaches ({len(failed)} -- do not retry identically):")
        for entry in failed[:5]:
            lines.append(f"  - {entry.get('tool')}: {str(entry.get('cause', ''))[:120]}")
    if summary.get("next_action"):
        lines.append("")
        lines.append(f"Next action: {summary['next_action']}")
    print("\n".join(lines))
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    """Normalize legacy session contracts in place (mode aliases only)."""
    try:
        from gravitas_policy import MODE_ALIASES, MODES
    except ModuleNotFoundError:
        print(json.dumps({"error": f"runtime assets not found under {ROOT}"}))
        return 1
    root = Path(args.root)
    session_base = root / ".gravitas" / "sessions"
    migrated, issues = [], []
    if session_base.is_dir():
        for contract_path in sorted(session_base.glob("*/contract.json")):
            try:
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                issues.append({"contract": str(contract_path), "issue": f"unreadable: {error}"})
                continue
            if not isinstance(contract, dict):
                issues.append({"contract": str(contract_path), "issue": "not an object"})
                continue
            mode = contract.get("mode")
            if mode in MODE_ALIASES:
                contract["mode"] = MODE_ALIASES[mode]
                contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
                migrated.append({"contract": str(contract_path),
                                 "mode": f"{mode} -> {contract['mode']}"})
            elif mode not in MODES:
                issues.append({"contract": str(contract_path), "issue": f"unknown mode: {mode!r}"})
            if not contract.get("acceptance_criteria"):
                issues.append({"contract": str(contract_path), "issue": "no acceptance criteria"})
    result = {"ok": True, "migrated": migrated, "issues": issues}
    print(json.dumps(result, indent=2))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """Report installed vs latest release (offline-tolerant)."""
    try:
        from importlib.metadata import version as package_version
        installed = package_version("gravitas")
    except Exception:  # noqa: BLE001 -- metadata may be absent in checkouts
        installed = "checkout"
    if not args.check:
        print(json.dumps({"installed": installed,
                          "hint": "run `gravitas update --check` to query PyPI, then `pip install -U gravitas`"}))
        return 0
    import urllib.request
    try:
        with urllib.request.urlopen("https://pypi.org/pypi/gravitas/json", timeout=10) as response:
            latest = json.loads(response.read())["info"]["version"]
    except Exception as error:  # noqa: BLE001 -- offline is an expected state
        print(json.dumps({"installed": installed, "latest": "unknown",
                          "reason": f"offline or unreachable: {error}"}))
        return 0
    print(json.dumps({"installed": installed, "latest": latest,
                      "update_available": installed != "checkout" and installed != latest}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="gravitas")
    sub = parser.add_subparsers(dest="subcommand", required=True)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("status").set_defaults(func=cmd_status)
    verify = sub.add_parser("verify"); verify.add_argument("--session-dir", required=True); verify.add_argument("--backfill-anchors", action="store_true", help="anchor the current head of a pre-existing ledger, then verify"); verify.set_defaults(func=cmd_verify)
    gc = sub.add_parser("gc"); gc.add_argument("--older-than-days", type=int, default=30); gc.add_argument("--apply", action="store_true", help="delete instead of reporting"); gc.set_defaults(func=cmd_gc)
    validator = sub.add_parser("validator"); validator.add_argument("--session-dir", required=True); validator.add_argument("--validator-id", required=True); validator.add_argument("--criterion-id", action="append", default=[]); validator.add_argument("command", nargs=argparse.REMAINDER); validator.set_defaults(func=cmd_validator)
    decide = sub.add_parser("decide", help="Emit a planning-policy record (planning, context/verification depth, delegation, reason codes) from --signals JSON")
    decide.add_argument("--signals", default="", help="JSON object of policy signals, e.g. '{\"dependent_files\": true, \"files\": 3}'")
    decide.set_defaults(func=cmd_decide)
    summarize = sub.add_parser("summarize", help="Emit the durable compact session state for handoff or resume")
    summarize.add_argument("--session-dir", required=True)
    summarize.set_defaults(func=cmd_summarize)
    context = sub.add_parser("context", help="Ranked repository context for changed files at a disclosure depth")
    context.add_argument("--root", default=".")
    context.add_argument("--changed", nargs="+", required=True)
    context.add_argument("--depth", default="dependency", choices=["target", "dependency", "subsystem"])
    context.set_defaults(func=cmd_context)
    validators = sub.add_parser("validators", help="Discover repo-aware validators and print an escalation plan")
    validators.add_argument("--root", default=".")
    validators.add_argument("--depth", default="targeted", choices=["targeted", "impact", "full"])
    validators.add_argument("--changed", nargs="*", default=[])
    validators.add_argument("--failure-evidence", action="store_true")
    validators.add_argument("--release", action="store_true")
    validators.set_defaults(func=cmd_validators)
    repro = sub.add_parser("repro", help="Run a bug reproducer bound to a criterion (reproduction-first protocol)")
    repro.add_argument("--session-dir", required=True)
    repro.add_argument("--criterion-id", required=True)
    repro.add_argument("--reproducer-id", help="Declared reproducer ID from the task contract")
    repro.add_argument("--phase", default="before", choices=["before", "after"])
    repro.add_argument("--unreproducible", action="store_true")
    repro.add_argument("--reason", default="")
    repro.add_argument("--cwd", default=".")
    repro.add_argument("command", nargs=argparse.REMAINDER)
    repro.set_defaults(func=cmd_repro)
    resolve = sub.add_parser("resolve-failure", help="Mark a failed fingerprint resolved so it can be retried")
    resolve.add_argument("--session-dir", required=True)
    resolve.add_argument("--fingerprint", required=True)
    resolve.add_argument("--reason", required=True)
    resolve.add_argument("--file", action="append", default=[],
                         help="Target file that must be re-read before completion (repeatable)")
    resolve.add_argument("--criterion-id", action="append", default=[],
                         help="Criterion requiring a fresh validator PASS (repeatable)")
    resolve.set_defaults(func=cmd_resolve_failure)
    edge = sub.add_parser("edge-cases", help="Expand seed values into deterministic boundary variants")
    edge.add_argument("--seeds", default="[]", help="JSON array of seed values")
    edge.set_defaults(func=cmd_edge_cases)
    guard = sub.add_parser("guard", help="Policy decision for a host envelope (used by the OpenCode plugin shim)")
    guard.add_argument("--envelope", default="", help="HostEnvelope JSON; reads stdin when empty")
    guard.add_argument("--contract", default="", help="Workspace contract JSON path (default: .gravitas/opencode-contract.json)")
    guard.set_defaults(func=cmd_guard)
    init = sub.add_parser("init", help="Scaffold host configuration (auto-detects opencode/antigravity markers)")
    init.add_argument("--host", default="auto", choices=["auto", "opencode", "antigravity"])
    init.add_argument("--profile", default="balanced", choices=["fast", "balanced", "strict"])
    init.add_argument("--root", default=".")
    init.set_defaults(func=cmd_init)
    explain = sub.add_parser("explain", help="Render a human-readable session explanation (state, evidence, next actions)")
    explain.add_argument("--session-dir", required=True)
    explain.add_argument("--json", action="store_true", help="Emit machine-readable summary instead of text")
    explain.set_defaults(func=cmd_explain)
    migrate = sub.add_parser("migrate", help="Migrate legacy session contracts (mode aliases, schema hygiene)")
    migrate.add_argument("--root", default=".")
    migrate.set_defaults(func=cmd_migrate)
    update = sub.add_parser("update", help="Check for a newer gravitas release (offline-tolerant)")
    update.add_argument("--check", action="store_true", help="Query PyPI for the latest version")
    update.set_defaults(func=cmd_update)
    bench = sub.add_parser("bench", help="GravitasBench reproducibility CLI (doctor, build-corpus, pilot, run, report)")
    bench.add_argument("bench_args", nargs=argparse.REMAINDER)
    bench.set_defaults(func=cmd_bench)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
