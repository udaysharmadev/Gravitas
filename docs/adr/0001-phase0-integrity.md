# ADR-0001: Phase 0 repository integrity fixes

Date: 2026-10-07 · Status: accepted · Commit: 793fe98

## Context

`git submodule status` failed (`no submodule mapping for benchmarks/legacy/L1`);
`gravitas doctor` failed on main (checked root `plugin.json`/`hooks.json` that
never existed there); the wheel shipped only `gravitas_cli.py`, so the
installed CLI crashed on `from evidence_chain import verify_chain`.

## Decisions

1. L1-L10 converted from orphan gitlinks to regular tracked fixture dirs.
   Rejected adding `.gitmodules`: the fixtures are single-commit calculator
   tasks; submodules are the wrong tool. `.bundle` exports preserve history.
2. CLI resolves assets as checkout (cwd, then module dir), then installed
   (`sys.prefix/share/gravitas`, mirroring repo layout), and imports
   `evidence_chain` lazily so `--help`/`doctor` never crash on import.
3. Wheel ships plugin manifests, hook scripts, agents, skill, and schemas via
   `data-files`. Rejected repackaging scripts as a Python package in Phase 0
   (would require rewriting flat cross-imports in 12 hook scripts; deferred
   to CLI/install UX phase).
4. `doctor` reports `mode` plus per-scope checks so checkout / installed /
   project failures point at the right layer.

## Verification

40 unit tests OK; wheel inspected (57 files); isolated-venv install +
`gravitas doctor` outside a checkout returns `mode: installed`, exit 0.
