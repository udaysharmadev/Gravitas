#!/usr/bin/env python3
"""Build a lightweight verification impact graph from changed source files."""
import argparse
import json
import re
from pathlib import Path


SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cs", ".rb", ".php"}
SKIP_PARTS = {".git", ".gravitas", "node_modules", "__pycache__", "dist", "build", "target"}


def source_files(root: Path):
    for path in root.rglob("*"):
        if path.suffix in SOURCE_SUFFIXES and not any(part in SKIP_PARTS for part in path.parts):
            yield path


def related_files(root: Path, changed: str) -> dict:
    changed_path = (root / changed).resolve() if not Path(changed).is_absolute() else Path(changed).resolve()
    name = changed_path.stem
    pattern = re.compile(rf"\b{re.escape(name)}\b")
    callers, tests = [], []
    for path in source_files(root):
        resolved = path.resolve()
        if resolved == changed_path:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        relative = str(path.relative_to(root))
        if pattern.search(text):
            (tests if "test" in path.name.lower() or "test" in path.parts else callers).append(relative)
    configs = [
        str(path.relative_to(root)) for path in root.iterdir()
        if path.name in {"pyproject.toml", "package.json", "tsconfig.json", "Cargo.toml", "go.mod", "pom.xml", "composer.json"}
    ]
    return {"callers": sorted(callers), "tests": sorted(tests), "config": sorted(configs)}


def build_impact_graph(root: Path, changed_files: list[str]) -> tuple[dict, list[str]]:
    graph = {changed: related_files(root, changed) for changed in sorted(set(changed_files))}
    targets = sorted({target for related in graph.values() for target in related["tests"] + related["config"]})
    return graph, targets


def main():
    parser = argparse.ArgumentParser(description="Build Gravitas verification impact targets")
    parser.add_argument("--root", default=".")
    parser.add_argument("--changed", nargs="+", required=True)
    args = parser.parse_args()
    graph, targets = build_impact_graph(Path(args.root).resolve(), args.changed)
    print(json.dumps({"impact_graph": graph, "verification_targets": targets}, indent=2))


if __name__ == "__main__":
    main()
