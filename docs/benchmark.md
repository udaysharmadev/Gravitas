# Benchmark Methodology

GravitasBench measures episodes (full trajectories + final repo state),
never final messages. Full protocol: `benchmarks/README.md`.

## What is measured

FSR, requirement coverage, regression/scope-violation rates, plan-only
violation rate, interruption recovery, false completion, evidence
integrity, solves-per-quota — all with Wilson 95% CIs; tokens/latency as
median + p90; paired McNemar tests; infrastructure failures classified
INVALID and excluded from denominators.

## Honesty gates (enforced in code)

- Reports render a research-preview banner unless every comparison has
  ≥30 valid paired episodes (`report.publication_ready`).
- Solver worktrees never contain acceptance tests; episodes record only
  `hidden_validator_hash`.
- Holdout tasks (L10) are refused in dev runs without `--include-holdout`.
- Primary comparison is within-model (treatment vs baseline, same model).
  Cross-model references are exploratory, published with exact revisions.
- Every marketing number must derive from a versioned raw artifact
  (`benchmarks/results/` + reproduce script + pinned commits).

## Current status

Registry: 30 task specs across 10 lanes. Fixtures are synthetic and
disposable (plumbing only, ineligible for publication). No release-grade
pinned repositories, no multi-family runs, no published results. See
`docs/production-readiness.md` for the gate board.
