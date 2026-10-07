"""Command line interface for Gravitas runtime operations."""
from __future__ import annotations

import argparse
import json
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
        "plugin_manifest": (native / "plugin.json").is_file(),
        "hooks": (native / "hooks.json").is_file(),
        "validator_runner": (SCRIPTS / "validator_runner.py").is_file(),
        "pre_tool_hook": (SCRIPTS / "pre_tool.py").is_file(),
        "stop_gate_hook": (SCRIPTS / "stop_gate.py").is_file(),
        "evidence_chain": (SCRIPTS / "evidence_chain.py").is_file(),
        "project_session_store": (Path.cwd() / ".gravitas" / "sessions").is_dir(),
    }
    print(json.dumps(checks, indent=2))
    required = ["skill", "plugin_manifest", "hooks", "validator_runner", "pre_tool_hook", "stop_gate_hook", "evidence_chain"]
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
    return module.main(["bench", *args.bench_args])


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
        from evidence_chain import verify_chain
    except ModuleNotFoundError:
        print(json.dumps({"valid": False, "reason": f"runtime assets not found under {ROOT}; reinstall gravitas or run from a checkout", "ledger": str(target)}))
        return 1
    valid, reason = verify_chain(target)
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


def main() -> int:
    parser = argparse.ArgumentParser(prog="gravitas")
    sub = parser.add_subparsers(dest="subcommand", required=True)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("status").set_defaults(func=cmd_status)
    verify = sub.add_parser("verify"); verify.add_argument("--session-dir", required=True); verify.set_defaults(func=cmd_verify)
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
    bench = sub.add_parser("bench", help="GravitasBench reproducibility CLI (doctor, build-corpus, pilot, run, report)")
    bench.add_argument("bench_args", nargs=argparse.REMAINDER)
    bench.set_defaults(func=cmd_bench)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
