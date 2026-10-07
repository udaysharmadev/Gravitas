# Contributing

## Architecture (read first)

`docs/adr/0001`–`0010`: integrity fixes, positioning, kernel/policy,
context, verification, action policy, host adapters, CLI, bench evidence.
The runtime is layered: normalized actions → policy → context →
verification/evidence → recovery, with thin host adapters. Every mechanism
needs a failure mode, an observable output, tests, and a reason it lives
in runtime rather than prompt prose.

## Test expectations

- Suite: `python -m unittest discover -s tests` (venv: `.venv/bin/python`).
  Must be green before any claim of done.
- New mechanisms require tests: unit + adversarial/bypass cases where
  policy is involved; fixture round-trips where hosts are involved.
- Never exact-retry a failure: change diagnosis, context, or strategy.
- Evidence before synthesis: cite command output, not intentions.
- Deterministic tests only: fixed seeds, temp dirs, no network, no model APIs.

## Change rules

- Read target + tests + callers before editing.
- Small reversible edits; coherent commits per phase with STATUS/WHY/EVIDENCE.
- Canonical sources only: never hand-edit `dist/` (rebuild via
  `scripts/build-native-bundle.sh`; CI checks drift).
- Public claims stay inside `scripts/check_readme_claims.py` guardrails.
- Schemas are versioned; migrations ship with the change.
