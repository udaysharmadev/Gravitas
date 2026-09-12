# GRAVITAS production-readiness gates

Last reviewed: 2026-09-12. This page separates release quality for the
distribution surface from evidence needed for comparative model claims.

| Gate | Status | Evidence / remaining boundary |
|---|---|---|
| Agent Skills format | PASS | `npx skills-ref validate skills/gravitas` passes. |
| Core project install | PASS | Clean skills CLI 1.5.26 install copied the full Core bundle to `.agents/skills/gravitas`. |
| Native plugin packaging | PASS | `agy` 1.2.1 accepted `dist/gravitas-antigravity` with one skill, three agents, and hooks; install, restage, and uninstall were exercised. |
| Runtime unit tests | PASS | Deterministic tests cover contracts, action locking, evidence, recovery, and benchmark plumbing. |
| Live hook trajectory | PARTIAL | Bundle staging and hook discovery were tested; a production model trajectory remains outside this install verification. |
| Benchmark corpus | PARTIAL | 30 task specifications across 10 planned lanes exist; release-grade pinned repositories and hidden validators do not. |
| Comparative results | BLOCKED | No eligible paired production dataset, uncertainty analysis, or raw trajectory release exists. |
| Public performance claims | BLOCKED | Do not publish FSR, coverage, false-completion, overhead, or model-gap claims until the prior gate passes. |

This is why the public project is a research preview even though Core and Native
installation paths are verified. See [install verification](install-verification.md)
and the [benchmark protocol](../benchmarks/README.md).
