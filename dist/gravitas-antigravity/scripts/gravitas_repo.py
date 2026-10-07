#!/usr/bin/env python3
"""Deterministic repository graph for the Gravitas Context Engine.

Normalized relations per file:

- defines: top-level symbols (functions, classes, interfaces, types)
- imports: raw module specifiers found in import statements
- imported_by: repo files whose imports resolve to this file (heuristic:
  the specifier's last path segment matches the file stem)
- callers: repo files referencing a defined symbol or importing the file
- tested_by: test/spec files covering it (path convention or import)
- configured_by: nearest config files walking up to the root
- co_changed: files frequently committed together (git log, bounded)

No vector database, no model calls, no full-repo loading by default: the
index is built once per root, cached under ``.gravitas/repo-index.json``
with mtime+size invalidation, and queries return ranked subsets with
reasons. Scores are ordinal ranking heuristics, not calibrated weights.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

INDEX_VERSION = 1
INDEX_NAME = "repo-index.json"
MAX_FILES = 20000
GIT_LOG_COMMITS = 50

SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
                   ".go", ".rs", ".java", ".cs", ".rb", ".php"}
SKIP_PARTS = {".git", ".gravitas", "node_modules", "__pycache__", "dist",
              "build", "target", "vendor", ".venv", "venv"}
CONFIG_NAMES = {"pyproject.toml", "package.json", "tsconfig.json", "Cargo.toml",
                "go.mod", "pom.xml", "build.gradle", "composer.json", "Makefile",
                "tox.ini", "setup.cfg", ".eslintrc", "eslint.config.js",
                "pytest.ini", "vitest.config.ts", "jest.config.js"}

SYMBOL_PATTERNS = (
    re.compile(r"^\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M),
    re.compile(r"^\s*(?:export\s+)?(?:class|interface|type|enum|function)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M),
    re.compile(r"^\s*(?:func\s+\(\w+\s+[\w*]+\))?\s*func\s+([A-Za-z_][A-Za-z0-9_]*)", re.M),
    re.compile(r"^\s*(?:pub\s+)?(?:fn|struct|enum|trait)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M),
)

IMPORT_PATTERNS = (
    re.compile(r"^\s*(?:import|from)\s+([A-Za-z0-9_./@-]+)", re.M),
    re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)"),
    re.compile(r"^\s*use\s+([A-Za-z0-9_:\\]+)", re.M),
)


def iter_source_files(root: Path):
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        count += 1
        if count > MAX_FILES:
            return
        yield path


def read_text(path: Path) -> str:
    try:
        if path.stat().st_size > 1_000_000:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def extract_symbols(text: str) -> list[str]:
    found: list[str] = []
    for pattern in SYMBOL_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            if name and name not in found:
                found.append(name)
    return found[:200]


def extract_imports(text: str) -> list[str]:
    found: list[str] = []
    for pattern in IMPORT_PATTERNS:
        for match in pattern.finditer(text):
            spec = match.group(1).strip().strip("'\"")
            if spec and spec not in found:
                found.append(spec)
    return found[:200]


def specifier_stem(spec: str) -> str:
    tail = spec.replace("\\", "/").split("/")[-1]
    tail = tail.split(".")[0] if "." in tail and not tail.startswith(".") else tail
    return tail.lstrip(".") or spec


def is_test_path(relative: str) -> bool:
    lowered = relative.lower()
    name = lowered.rsplit("/", 1)[-1]
    return (name.startswith("test_") or name.endswith("_test.py")
            or ".test." in name or ".spec." in name or "/test/" in lowered
            or "/tests/" in lowered or lowered.startswith("test"))


def co_changed_pairs(root: Path) -> dict[str, dict[str, int]]:
    """Map file -> {co-committed file: count} from recent git history."""
    try:
        result = subprocess.run(
            ["git", "log", f"-n{GIT_LOG_COMMITS}", "--name-only", "--pretty=format:COMMIT:%H"],
            cwd=root, text=True, capture_output=True, check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}
    pairs: dict[str, dict[str, int]] = {}
    current: list[str] = []

    def flush(files: list[str]) -> None:
        unique = sorted(set(files))
        if len(unique) > 1:
            for left in unique:
                bucket = pairs.setdefault(left, {})
                for right in unique:
                    if right != left:
                        bucket[right] = bucket.get(right, 0) + 1

    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("COMMIT:"):
            flush(current)
            current = []
        elif stripped:
            current.append(stripped)
    flush(current)
    return pairs


def build_index(root: Path) -> dict:
    root = root.resolve()
    files: dict[str, dict] = {}
    for path in iter_source_files(root):
        relative = str(path.relative_to(root))
        text = read_text(path)
        try:
            stat = path.stat()
            fingerprint = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            continue
        files[relative] = {
            "symbols": extract_symbols(text),
            "imports": extract_imports(text),
            "test": is_test_path(relative),
            "fingerprint": list(fingerprint),
        }
    stems: dict[str, list[str]] = {}
    for relative in files:
        stems.setdefault(Path(relative).stem, []).append(relative)
    index = {"version": INDEX_VERSION, "root": str(root), "files": files}
    _attach_relations(index, root)
    return index


def _attach_relations(index: dict, root: Path) -> None:
    files = index["files"]
    stems: dict[str, list[str]] = {}
    for relative in files:
        stems.setdefault(Path(relative).stem, []).append(relative)
    for relative, info in files.items():
        importers = sorted({
            other for other, other_info in files.items() if other != relative
            for spec in other_info["imports"]
            if relative in stems.get(specifier_stem(spec), [])})
        info["imported_by"] = importers
        info["callers"] = sorted(importers)
    # Symbol references need file text; resolved in a second pass below.
    texts = {relative: read_text(root / relative) for relative in files}
    for relative, info in files.items():
        if info["symbols"]:
            pattern = re.compile(r"\b(?:" + "|".join(re.escape(s) for s in info["symbols"]) + r")\b")
            for other in files:
                if other == relative:
                    continue
                if pattern.search(texts.get(other, "")):
                    if other not in info["callers"]:
                        info["callers"].append(other)
            info["callers"] = sorted(info["callers"])
        info["tested_by"] = sorted(
            other for other in files
            if other != relative and files[other]["test"]
            and (other in info["callers"] or other in info["imported_by"]
                 or Path(relative).stem in other))
        info["configured_by"] = sorted(configured_by(root, relative))
    pairs = co_changed_pairs(root)
    for relative, info in files.items():
        bucket = pairs.get(relative, {})
        info["co_changed"] = sorted(bucket, key=lambda name: (-bucket[name], name))[:10]


def configured_by(root: Path, relative: str) -> list[str]:
    found = []
    directory = (root / relative).parent
    while True:
        try:
            for child in directory.iterdir():
                if child.name in CONFIG_NAMES:
                    found.append(str(child.relative_to(root)))
        except OSError:
            pass
        if directory == root or root not in directory.parents:
            break
        directory = directory.parent
    return found


def index_path(root: Path) -> Path:
    return root.resolve() / ".gravitas" / INDEX_NAME


def load_index(root: Path) -> dict | None:
    path = index_path(root)
    if not path.exists():
        return None
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(index, dict) or index.get("version") != INDEX_VERSION:
        return None
    if index.get("root") != str(root.resolve()):
        return None
    return index


def refresh_index(root: Path, index: dict) -> dict:
    """Rebuild entries whose mtime/size changed; drop deleted files."""
    root = root.resolve()
    files = index.get("files", {})
    changed = False
    for relative in list(files):
        path = root / relative
        try:
            stat = path.stat()
            fingerprint = [stat.st_mtime_ns, stat.st_size]
        except OSError:
            del files[relative]
            changed = True
            continue
        if files[relative].get("fingerprint") != fingerprint:
            text = read_text(path)
            files[relative].update({
                "symbols": extract_symbols(text),
                "imports": extract_imports(text),
                "test": is_test_path(relative),
                "fingerprint": fingerprint,
            })
            changed = True
    current = {str(p.relative_to(root)) for p in iter_source_files(root)}
    for relative in list(files):
        if relative not in current:
            del files[relative]
            changed = True
    for relative in current:
        if relative not in files:
            path = root / relative
            text = read_text(path)
            try:
                stat = path.stat()
                fingerprint = [stat.st_mtime_ns, stat.st_size]
            except OSError:
                continue
            files[relative] = {
                "symbols": extract_symbols(text),
                "imports": extract_imports(text),
                "test": is_test_path(relative),
                "fingerprint": list(fingerprint),
            }
            changed = True
    _attach_relations(index, root)
    return index


def get_index(root: Path, *, refresh: bool = True) -> dict:
    root = root.resolve()
    index = load_index(root)
    if index is None:
        index = build_index(root)
        save_index(root, index)
        return index
    if refresh:
        index = refresh_index(root, index)
        save_index(root, index)
    return index


def save_index(root: Path, index: dict) -> None:
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Retrieval: ranked, reasoned, depth-bounded.
# ---------------------------------------------------------------------------

def rank_related(index: dict, target: str) -> list[dict]:
    """Rank files related to target with explicit reasons (ordinal only)."""
    info = index.get("files", {}).get(target)
    if not info:
        return []
    scored: dict[str, dict] = {}

    def add(path: str, points: int, reason: str):
        if path == target or path not in index["files"]:
            return
        entry = scored.setdefault(path, {"path": path, "score": 0, "reasons": []})
        entry["score"] += points
        if reason not in entry["reasons"]:
            entry["reasons"].append(reason)

    for path in info.get("imported_by", []):
        add(path, 3, "imports-target")
    for path in info.get("callers", []):
        add(path, 2, "references-symbol")
    for path in info.get("tested_by", []):
        add(path, 3, "covers-target")
    for path in info.get("configured_by", []):
        add(path, 1, "configures-target")
    for path in info.get("co_changed", []):
        add(path, 2, "co-changed")
    same_dir = str(Path(target).parent)
    for path in index["files"]:
        if path != target and str(Path(path).parent) == same_dir:
            add(path, 1, "same-directory")
    ranked = sorted(scored.values(), key=lambda e: (-e["score"], e["path"]))
    for entry in ranked:
        entry["reasons"] = sorted(entry["reasons"])
    return ranked


def context_for(index: dict, changed: list[str], depth: str) -> dict:
    """Progressive disclosure: target -> dependency -> subsystem."""
    changed = [c for c in dict.fromkeys(changed) if c in index.get("files", {})]
    related: dict[str, dict] = {}
    if depth in ("dependency", "subsystem"):
        for target in changed:
            for entry in rank_related(index, target):
                current = related.setdefault(entry["path"], entry)
                if entry["score"] > current["score"]:
                    related[entry["path"]] = entry
    if depth == "subsystem":
        second_hop: dict[str, dict] = {}
        for entry in list(related.values())[:10]:
            for hop in rank_related(index, entry["path"])[:5]:
                if hop["path"] not in related and hop["path"] not in changed:
                    hop = dict(hop, reasons=sorted(set(hop["reasons"]) | {"second-hop"}))
                    current = second_hop.setdefault(hop["path"], hop)
                    if hop["score"] > current["score"]:
                        second_hop[hop["path"]] = hop
        related.update(second_hop)
    if depth == "target":
        files = list(changed)
    else:
        files = list(changed) + sorted(related, key=lambda p: (-related[p]["score"], p))
    return {
        "depth": depth,
        "files": files[:60],
        "reasons": {path: related[path]["reasons"] for path in files if path in related},
    }
