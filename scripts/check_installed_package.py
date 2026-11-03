#!/usr/bin/env python3
"""Check an installed wheel from disposable projects outside the checkout."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path


def run_json(command: list[str], cwd: Path, env: dict[str, str]) -> dict:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                            text=True, check=False, timeout=60)
    if result.returncode:
        raise RuntimeError(f"{command!r} failed ({result.returncode}): {result.stdout}{result.stderr}")
    return json.loads(result.stdout)


def snapshot(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def check_install() -> dict:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}
    with tempfile.TemporaryDirectory(prefix="gravitas-installed-") as directory:
        root = Path(directory)
        blank = root / "blank"
        blank.mkdir()
        info = run_json(
            [sys.executable, "-c", "import gravitas_cli,json; print(json.dumps({'module':gravitas_cli.__file__,'mode':gravitas_cli.runtime_mode(),'root':str(gravitas_cli.ROOT)}))"],
            blank, env,
        )
        if info["mode"] != "installed":
            raise RuntimeError(f"expected installed runtime, got {info!r}")
        executable = "gravitas.exe" if os.name == "nt" else "gravitas"
        script_dirs = [Path(sysconfig.get_path("scripts"))]
        module_dir = Path(info["module"]).resolve().parent
        for scheme in sysconfig.get_scheme_names():
            if scheme.endswith("_user") and module_dir in {
                Path(sysconfig.get_path(kind, scheme=scheme)).resolve() for kind in ("purelib", "platlib")
            }:
                script_dirs.insert(0, Path(sysconfig.get_path("scripts", scheme=scheme)))
        cli = next((path / executable for path in script_dirs if (path / executable).is_file()), None)
        if cli is None:
            raise RuntimeError("installed gravitas console entry point is missing")
        doctor = run_json([str(cli), "doctor"], blank, env)
        if doctor["mode"] != "installed":
            raise RuntimeError("console entry point did not use installed assets")
        decision = run_json([str(cli), "decide", "--signals", "{}"], blank, env)
        if decision.get("planning") != "direct":
            raise RuntimeError(f"unexpected planning result: {decision!r}")

        project = root / "opencode-project"
        project.mkdir()
        original = {"model": "local-test-model", "permission": {"read": "allow", "edit": "deny"}}
        (project / "opencode.json").write_text(json.dumps(original), encoding="utf-8")
        result = run_json([str(cli), "init", "--host", "opencode", "--root", str(project)], project, env)
        if not result.get("ok"):
            raise RuntimeError(f"OpenCode init failed: {result!r}")
        for relative in (
            ".agents/skills/gravitas/SKILL.md", ".agents/skills/gravitas-highstakes/SKILL.md",
            ".opencode/plugins/gravitas.js", ".gravitas/opencode-contract.json", "AGENTS.md",
        ):
            if not (project / relative).is_file():
                raise RuntimeError(f"installed init omitted {relative}")
        actual = json.loads((project / "opencode.json").read_text(encoding="utf-8"))
        if any(actual.get(key) != value for key, value in original.items()):
            raise RuntimeError("OpenCode init overwrote existing configuration")
        before = snapshot(project)
        repeated = run_json([str(cli), "init", "--host", "opencode", "--root", str(project)], project, env)
        if not repeated.get("ok") or snapshot(project) != before:
            raise RuntimeError("repeated init was not idempotent")

        native = root / "native-project"
        native.mkdir()
        result = run_json([str(cli), "init", "--host", "antigravity", "--root", str(native)], native, env)
        if not result.get("ok") or not (native / ".agents/skills/gravitas/SKILL.md").is_file():
            raise RuntimeError("Antigravity skill initialization failed")
        return {"mode": info["mode"], "runtime_root": info["root"],
                "python": sys.version.split()[0], "hosts": ["opencode", "antigravity"]}


def main() -> int:
    try:
        result = check_install()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL installed package: {error}", file=sys.stderr)
        return 1
    print("PASS installed package: " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
