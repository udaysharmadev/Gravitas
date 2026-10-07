#!/usr/bin/env python3
"""Repository-aware validator discovery and escalation planning.

Inspects actual project configuration -- package.json scripts, pyproject /
pytest config, tox/nox, Makefile targets, Cargo.toml, go.mod, Gradle/Maven
files, CI workflows, and present test directories -- and builds a validator
catalog with provenance. Nothing is assumed from language alone: a validator
enters the catalog only with (a) a config file that declares it and (b) a
resolvable executable or a project-local script that names it.

Escalation (targeted -> impacted neighborhood -> broader regression ->
release/full CI) is chosen from the policy verification depth, blast
radius, and failure evidence -- never by running everything blindly.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

CONFIG_FILES = (
    "package.json", "pyproject.toml", "pytest.ini", "tox.ini", "noxfile.py",
    "Makefile", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "build.gradle.kts", "composer.json", "Gemfile", ".github",
)

#: tool -> (config evidence, executable names). Both must hold.
TOOL_EVIDENCE = {
    "pytest": (("pyproject.toml", "pytest.ini", "tox.ini", "tests", "test"), ("pytest",)),
    "vitest": (("package.json", "vitest.config.ts", "vitest.config.js"), ("npx", "npm", "yarn", "pnpm", "bun")),
    "jest": (("package.json", "jest.config.js"), ("npx", "npm", "yarn", "pnpm")),
    "go-test": (("go.mod",), ("go",)),
    "cargo-test": (("Cargo.toml",), ("cargo",)),
    "rspec": (("Gemfile", "spec"), ("bundle", "rspec")),
    "phpunit": (("composer.json", "phpunit.xml"), ("vendor/bin/phpunit", "phpunit")),
    "mypy": (("pyproject.toml", "mypy.ini", "setup.cfg"), ("mypy",)),
    "ruff": (("pyproject.toml", "ruff.toml", ".ruff.toml"), ("ruff",)),
    "eslint": (("package.json", "eslint.config.js", ".eslintrc"), ("npx", "npm")),
    "tsc": (("package.json", "tsconfig.json"), ("npx", "npm", "tsc")),
    "clippy": (("Cargo.toml",), ("cargo",)),
    "go-vet": (("go.mod",), ("go",)),
}


def _read_text(path: Path, limit: int = 200_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _has_marker(root: Path, marker: str) -> bool:
    candidate = root / marker
    if candidate.exists():
        return True
    if "/" not in marker and marker not in (".github",):
        for path in root.rglob(marker):
            if ".git" in path.parts or "node_modules" in path.parts:
                continue
            return True
    return False


def _has_executable(root: Path, names: tuple) -> str | None:
    for name in names:
        if "/" in name:
            if (root / name).exists():
                return name
            continue
        if shutil.which(name):
            return name
    return None


def _package_json_scripts(root: Path) -> dict:
    path = root / "package.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(_read_text(path))
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts")
    return scripts if isinstance(scripts, dict) else {}


def _makefile_targets(root: Path) -> list[str]:
    path = root / "Makefile"
    if not path.exists():
        return []
    targets = []
    for line in _read_text(path).splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?!:=)", line)
        if match:
            targets.append(match.group(1))
    return targets


def _ci_workflows(root: Path) -> list[str]:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return []
    return sorted(p.name for p in workflows.iterdir() if p.suffix in (".yml", ".yaml"))


def discover_validators(root: Path) -> dict:
    """Build the validator catalog for a repository root.

    Returns {"root": ..., "validators": [...], "ci": [...]}. Each validator:
    {id, kind, command[], provenance[], scope}. Empty catalog when nothing
    is discoverable -- callers must say so, not invent commands.
    """
    root = root.resolve()
    validators: list[dict] = []
    scripts = _package_json_scripts(root)
    make_targets = _makefile_targets(root)

    for tool, (markers, executables) in TOOL_EVIDENCE.items():
        evidence = [m for m in markers if _has_marker(root, m)]
        if not evidence:
            continue
        binary = _has_executable(root, executables)
        if not binary:
            continue
        provenance = [f"config:{m}" for m in evidence] + [f"binary:{binary}"]
        validators.append(_validator_for(tool, binary, root, scripts, make_targets, provenance))

    for name in ("test", "check", "lint", "typecheck", "verify"):
        if name in scripts:
            validators.append({
                "id": f"npm-{name}", "kind": "suite",
                "command": ["npm", "run", name],
                "provenance": ["config:package.json", "script:" + name],
                "scope": "project",
            })
    for target in make_targets:
        if target in ("test", "check", "lint", "verify") and not any(
                v["id"] == f"make-{target}" for v in validators):
            validators.append({
                "id": f"make-{target}", "kind": "suite",
                "command": ["make", target],
                "provenance": ["config:Makefile", "target:" + target],
                "scope": "project",
            })
    validators.sort(key=lambda v: v["id"])
    return {"root": str(root), "validators": validators, "ci": _ci_workflows(root)}


def _validator_for(tool: str, binary: str, root: Path, scripts: dict,
                   make_targets: list[str], provenance: list[str]) -> dict:
    if tool == "pytest":
        return {"id": "pytest", "kind": "test", "command": [binary, "-q"],
                "provenance": provenance, "scope": "project"}
    if tool == "vitest":
        run = ["npx", "vitest", "run"] if binary == "npx" else [binary, "run", "vitest"]
        return {"id": "vitest", "kind": "test", "command": run,
                "provenance": provenance, "scope": "project"}
    if tool == "jest":
        return {"id": "jest", "kind": "test",
                "command": [binary, "jest"] if binary == "npx" else [binary, "run", "jest"],
                "provenance": provenance, "scope": "project"}
    if tool == "go-test":
        return {"id": "go-test", "kind": "test", "command": ["go", "test", "./..."],
                "provenance": provenance, "scope": "project"}
    if tool == "cargo-test":
        return {"id": "cargo-test", "kind": "test", "command": ["cargo", "test"],
                "provenance": provenance, "scope": "project"}
    if tool == "rspec":
        return {"id": "rspec", "kind": "test", "command": [binary, "exec", "rspec"],
                "provenance": provenance, "scope": "project"}
    if tool == "phpunit":
        command = [binary] if "/" in binary else [binary]
        return {"id": "phpunit", "kind": "test", "command": command,
                "provenance": provenance, "scope": "project"}
    if tool == "mypy":
        return {"id": "mypy", "kind": "type", "command": [binary, "."],
                "provenance": provenance, "scope": "project"}
    if tool == "ruff":
        return {"id": "ruff", "kind": "lint", "command": [binary, "check", "."],
                "provenance": provenance, "scope": "project"}
    if tool == "eslint":
        return {"id": "eslint", "kind": "lint", "command": [binary, "eslint", "."] if binary == "npx" else [binary, "run", "lint"],
                "provenance": provenance, "scope": "project"}
    if tool == "tsc":
        return {"id": "tsc", "kind": "type", "command": [binary, "tsc", "--noEmit"] if binary == "npx" else [binary, "run", "typecheck"],
                "provenance": provenance, "scope": "project"}
    if tool == "clippy":
        return {"id": "clippy", "kind": "lint", "command": ["cargo", "clippy"],
                "provenance": provenance, "scope": "project"}
    if tool == "go-vet":
        return {"id": "go-vet", "kind": "static", "command": ["go", "vet", "./..."],
                "provenance": provenance, "scope": "project"}
    return {"id": tool, "kind": "unknown", "command": [binary],
            "provenance": provenance, "scope": "project"}


# ---------------------------------------------------------------------------
# Escalation planning.
# ---------------------------------------------------------------------------

def escalation_plan(catalog: dict, *, verification_depth: str,
                    changed: list[str], related: dict,
                    failure_evidence: bool = False,
                    release_context: bool = False) -> dict:
    """Choose validator subsets per escalation rung.

    Rungs: targeted (changed-file tests) -> impact (related tests/configs)
    -> suite (project test validators) -> full (everything incl. CI signal).
    Expansion beyond targeted requires a reason: depth, blast radius,
    failure evidence, or release context.
    """
    validators = {v["id"]: v for v in catalog.get("validators", [])}
    test_ids = sorted(v["id"] for v in validators.values() if v["kind"] == "test")
    other_ids = sorted(v["id"] for v in validators.values() if v["kind"] != "test")
    reasons = [f"verification_depth={verification_depth}"]
    if failure_evidence:
        reasons.append("failure-evidence")
    if release_context:
        reasons.append("release-context")

    plan: dict = {"reasons": sorted(reasons), "rungs": {}}
    plan["rungs"]["targeted"] = {
        "validators": test_ids,
        "files": sorted(set(changed)),
        "note": "run test validators scoped to changed files where the runner supports file args",
    }
    impact_files = sorted({p for paths in related.values() for p in paths} | set(changed))
    expand = (verification_depth in ("impact", "full") or failure_evidence or release_context)
    plan["rungs"]["impact"] = {
        "validators": test_ids if expand else [],
        "files": impact_files if expand else [],
        "note": "expanded" if expand else "skipped: targeted depth, no failure or release signal",
    }
    suite_expand = verification_depth == "full" or failure_evidence or release_context
    plan["rungs"]["suite"] = {
        "validators": test_ids + other_ids if suite_expand else [],
        "note": "expanded" if suite_expand else "skipped: no full-depth, failure, or release signal",
    }
    plan["rungs"]["full"] = {
        "validators": test_ids + other_ids if release_context else [],
        "ci": catalog.get("ci", []) if release_context else [],
        "note": "release context" if release_context else "skipped: not a release",
    }
    return plan


# ---------------------------------------------------------------------------
# Adversarial edge-case expansion (deterministic, no model needed).
# ---------------------------------------------------------------------------

NUMERIC_BOUNDARIES = ["0", "-1", "1", "2147483647", "-2147483648", "1.5", "-0.0"]
STRING_BOUNDARIES = ["", " ", "a", "A" * 10000, "null", "undefined", "None",
                     "0", "-1", "ünïcodé✓", "line1\nline2", "\t", "' OR '1'='1"]
COLLECTION_BOUNDARIES = ["[]", "{}", "[null]", "[0]", '""']


def expand_cases(seeds: list) -> list[dict]:
    """Expand seed values into boundary variants with reasons.

    Deterministic and duplicate-free. The agent executes variants through a
    trusted project validator; surprises become regression tests.
    """
    variants: list[dict] = []
    seen: set[str] = set()

    def add(value: str, reason: str):
        if value not in seen:
            seen.add(value)
            variants.append({"value": value, "reason": reason})

    for seed in seeds:
        text = seed if isinstance(seed, str) else json.dumps(seed)
        add(text, "seed-as-given")
        if re.fullmatch(r"-?\d+(\.\d+)?", text):
            for boundary in NUMERIC_BOUNDARIES:
                add(boundary, f"numeric-boundary vs seed {text}")
            add("", "empty vs numeric seed")
        elif text in ("[]", "{}", "[null]", "[0]"):
            for boundary in COLLECTION_BOUNDARIES:
                add(boundary, f"collection-boundary vs seed {text}")
        else:
            for boundary in STRING_BOUNDARIES:
                add(boundary, f"string-boundary vs seed {text}")
    return variants
