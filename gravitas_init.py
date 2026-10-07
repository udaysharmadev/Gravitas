"""Project scaffolding for Gravitas host adapters (`gravitas init`).

Copies adapter templates into a project directory without clobbering
existing user configuration: JSON is merged per-key, AGENTS.md is
extended inside idempotent markers, and existing files are never
overwritten (reported as skipped).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

AGENTS_START = "<!-- GRAVITAS-OPENCODE-START"
AGENTS_END = "GRAVITAS-OPENCODE-END -->"


def detect_hosts(root: Path) -> list[str]:
    """Detect configured hosts from project markers (no guessing)."""
    root = Path(root)
    hosts = []
    if ((root / "opencode.json").exists() or (root / "opencode.jsonc").exists()
            or (root / ".opencode").is_dir()):
        hosts.append("opencode")
    if (root / ".agents").is_dir() or (root / "AGENTS.md").exists():
        hosts.append("antigravity")
    return hosts


def detect_ecosystem(root: Path) -> dict:
    """Describe language and discovered validators for init output."""
    try:
        from gravitas_verify import discover_validators
        catalog = discover_validators(Path(root))
        return {"validators": catalog["validators"], "ci": catalog.get("ci", [])}
    except Exception:  # noqa: BLE001 -- discovery is advisory; init must not fail
        return {"validators": [], "ci": []}


def _copy_tree(source: Path, dest: Path, installed: list, skipped: list) -> None:
    for item in sorted(source.rglob("*")):
        if item.is_dir():
            continue
        relative = item.relative_to(source)
        target = dest / relative
        if target.exists():
            skipped.append(str(target))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        installed.append(str(target))


def _merge_json(target: Path, fragment: dict, installed: list, skipped: list) -> None:
    current = {}
    if target.exists():
        try:
            current = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = {}
    if not isinstance(current, dict):
        current = {}
    changed = False
    for key, value in fragment.items():
        if key not in current:
            current[key] = value
            changed = True
    if not target.exists() or changed:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        installed.append(str(target))
    else:
        skipped.append(str(target))


def _ensure_agents_block(agents_md: Path, snippet: str, installed: list, skipped: list) -> None:
    if agents_md.exists():
        text = agents_md.read_text(encoding="utf-8")
        if AGENTS_START in text:
            skipped.append(str(agents_md))
            return
        text = text.rstrip("\n") + "\n\n" + snippet
    else:
        text = "# Project Instructions\n\n" + snippet
    agents_md.write_text(text, encoding="utf-8")
    installed.append(str(agents_md))


def init_opencode(root: Path, *, profile: str = "balanced", source_root: Path) -> dict:
    """Install OpenCode support into a project directory."""
    root = Path(root).resolve()
    source_root = Path(source_root).resolve()
    adapter = source_root / "adapters" / "opencode"
    installed: list[str] = []
    skipped: list[str] = []

    for skill in ("gravitas", "gravitas-highstakes"):
        _copy_tree(source_root / "skills" / skill, root / ".agents" / "skills" / skill,
                   installed, skipped)
    _copy_tree(adapter / "agents", root / ".opencode" / "agents", installed, skipped)
    _copy_tree(adapter / "plugin", root / ".opencode" / "plugins", installed, skipped)

    profile_path = adapter / "permissions" / f"{profile}.json"
    if not profile_path.exists():
        return {"ok": False, "error": f"unknown profile: {profile}"}
    fragment = json.loads(profile_path.read_text(encoding="utf-8"))
    fragment.pop("$schema", None)
    _merge_json(root / "opencode.json", fragment, installed, skipped)

    snippet = (adapter / "AGENTS-snippet.md").read_text(encoding="utf-8")
    _ensure_agents_block(root / "AGENTS.md", snippet, installed, skipped)

    contract_target = root / ".gravitas" / "opencode-contract.json"
    if contract_target.exists():
        skipped.append(str(contract_target))
    else:
        contract_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(adapter / "contract-template.json", contract_target)
        installed.append(str(contract_target))

    # Discovered validators are reported, not auto-bound: binding a
    # validator to acceptance criteria is a task decision, not scaffolding.
    ecosystem = detect_ecosystem(root)
    return {"ok": True, "host": "opencode", "profile": profile,
            "root": str(root), "installed": installed, "skipped": skipped,
            "detected_validators": [v["id"] for v in ecosystem["validators"]],
            "detected_ci": ecosystem["ci"]}


def init_antigravity(root: Path, *, source_root: Path) -> dict:
    """Install workspace skills for Antigravity; the Native plugin installs via agy."""
    root = Path(root).resolve()
    source_root = Path(source_root).resolve()
    installed: list[str] = []
    skipped: list[str] = []
    for skill in ("gravitas", "gravitas-highstakes"):
        _copy_tree(source_root / "skills" / skill, root / ".agents" / "skills" / skill,
                   installed, skipped)
    return {"ok": True, "host": "antigravity", "root": str(root),
            "installed": installed, "skipped": skipped,
            "next": "agy plugin install <path-to>/dist/gravitas-antigravity"}
