#!/usr/bin/env python3
"""Build verification impact targets from changed source files.

Backed by the deterministic repository graph (gravitas_repo): real import
edges, symbol references, test association, config discovery, and git
co-change history. Output shape keeps the legacy keys (callers, tests,
config) and adds importers, symbols, and co_changed.
"""
import argparse
import json
from pathlib import Path

from gravitas_repo import context_for, get_index


def _normalize_changed(root: Path, changed: str) -> str | None:
    candidate = Path(changed)
    if candidate.is_absolute():
        try:
            relative = str(candidate.resolve().relative_to(root))
        except ValueError:
            return None
    else:
        relative = changed
    if (root / relative).is_file():
        return relative
    return None


def related_files(root: Path, changed: str) -> dict:
    """Legacy-compatible per-file relations, graph-backed."""
    index = get_index(root)
    relative = _normalize_changed(root, changed)
    if relative is None or relative not in index.get("files", {}):
        return {"callers": [], "tests": [], "config": [],
                "importers": [], "symbols": [], "co_changed": []}
    info = index["files"][relative]
    return {
        "callers": info.get("callers", []),
        "tests": info.get("tested_by", []),
        "config": info.get("configured_by", []),
        "importers": info.get("imported_by", []),
        "symbols": info.get("symbols", []),
        "co_changed": info.get("co_changed", []),
    }


def build_impact_graph(root: Path, changed_files: list[str]) -> tuple[dict, list[str]]:
    root = root.resolve()
    graph = {}
    for changed in sorted(set(changed_files)):
        relative = _normalize_changed(root, changed) or changed
        graph[relative] = related_files(root, changed)
    targets = sorted({target for related in graph.values()
                      for target in related["tests"] + related["config"]})
    return graph, targets


def verification_context(root: Path, changed_files: list[str], depth: str = "dependency") -> dict:
    """Progressive-disclosure file set for a verification depth."""
    root = root.resolve()
    index = get_index(root)
    normalized = [rel for c in changed_files if (rel := _normalize_changed(root, c))]
    return context_for(index, normalized, depth)


def main():
    parser = argparse.ArgumentParser(description="Build Gravitas verification impact targets")
    parser.add_argument("--root", default=".")
    parser.add_argument("--changed", nargs="+", required=True)
    parser.add_argument("--depth", default="dependency",
                        choices=["target", "dependency", "subsystem"])
    args = parser.parse_args()
    root = Path(args.root).resolve()
    graph, targets = build_impact_graph(root, args.changed)
    print(json.dumps({
        "impact_graph": graph,
        "verification_targets": targets,
        "context": verification_context(root, args.changed, args.depth),
    }, indent=2))


if __name__ == "__main__":
    main()
