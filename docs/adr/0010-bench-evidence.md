# ADR-0010: Solver-blind benchmark acceptance

Date: 2026-10-07 · Status: accepted

## Context

Synthetic fixture acceptance tests lived inside the solver worktree: the
solver could read the grading test, and "solve" meant passing a visible
test. The bench CLI was an unimplemented stub (nonzero exits, ignored
argv), ablations did not exist, and holdout discipline was unenforced.

## Decisions

1. Fixtures split: solver worktree gets the broken implementation plus an
   import smoke test only. Acceptance tests generate deterministically but
   materialize runner-private, execute post-trajectory, and record only
   `hidden_validator_hash` in the episode. Development vs. hidden
   validators are now structurally separate.
2. Holdout (L10 long-horizon tasks) enforced in the runner: dev runs
   refuse them without `--include-holdout`. Synthetic fixtures cannot leak
   training data (generated per task), but the pipeline is exercised now
   so real fixtures inherit it.
3. Ablation configs (`configurations-ablation`) isolate enforcement /
   context / verification against full Gravitas on the same model.
   Reference configs stay exploratory.
4. `benchmarks/cli.py` rewritten as a real surface (doctor/build-corpus/
   run/report) with argv respected; the fake pilot stub removed. `gravitas
   bench` delegation fixed accordingly.
5. Held-out runner work (metrics Wilson CIs, benchstats Mann-Whitney,
   randomize block design, claim-gated report) reviewed and committed;
   superseded archive committed with its provenance README.

## Non-changes

Fixtures remain synthetic and ineligible for published comparisons
(report gate: 30 paired episodes minimum). Licensed real fixtures, hidden
validators for real repos, and multi-family runs are Phase 10+ work.

## Verification

Bench tests cover solver-blindness (acceptance absent, smoke passes,
hidden fails pre-fix), determinism, holdout gating, and ablation registry
validity; audit still passes; full gate green.
