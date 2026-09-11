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


def runtime_root() -> Path:
    """Prefer the native plugin checkout when the console script is installed."""
    checkout = Path.cwd()
    if (checkout / "plugins" / "gravitas-antigravity" / "scripts").is_dir():
        return checkout
    return MODULE_ROOT


ROOT = runtime_root()
SCRIPTS = ROOT / "plugins" / "gravitas-antigravity" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from evidence_chain import verify_chain  # noqa: E402


def sessions(root: Path) -> list[Path]:
    directory = root / ".gravitas" / "sessions"
    return sorted((path for path in directory.iterdir() if path.is_dir()), key=lambda path: path.stat().st_mtime, reverse=True) if directory.exists() else []


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = {
        "skill": (ROOT / "skills/gravitas/SKILL.md").is_file(),
        "plugin_manifest": (ROOT / "plugin.json").is_file(),
        "hooks": (ROOT / "hooks.json").is_file(),
        "validator_runner": (SCRIPTS / "validator_runner.py").is_file(),
    }
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


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


def main() -> int:
    parser = argparse.ArgumentParser(prog="gravitas")
    sub = parser.add_subparsers(dest="subcommand", required=True)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("status").set_defaults(func=cmd_status)
    verify = sub.add_parser("verify"); verify.add_argument("--session-dir", required=True); verify.set_defaults(func=cmd_verify)
    gc = sub.add_parser("gc"); gc.add_argument("--older-than-days", type=int, default=30); gc.add_argument("--apply", action="store_true", help="delete instead of reporting"); gc.set_defaults(func=cmd_gc)
    validator = sub.add_parser("validator"); validator.add_argument("--session-dir", required=True); validator.add_argument("--validator-id", required=True); validator.add_argument("--criterion-id", action="append", default=[]); validator.add_argument("command", nargs=argparse.REMAINDER); validator.set_defaults(func=cmd_validator)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
