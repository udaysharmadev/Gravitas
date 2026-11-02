# Next-Generation Roadmap

Parent epic: this file. Child issues are created on GitHub (links below) and
deduplicated against issue #27. Priority: P0 correctness/security/bench
blockers, P1 high-impact, P2 experimental, plus research/host/integration.

## P0 — Correctness / security / benchmark blockers
- [ ] #27 Bench report pipeline never validates episodes — fixed on
  `ascension/phase-b-foundation` (schema-gated `cmd_report` + empty/aggregate
  guards + regression tests); merge vs contributor PR #56, then close.
- [ ] #68 Ledger rewrite without anchor passes verification (evidence forgery).
- [ ] #70 Lifecycle fixture corpus + stale-shim detection (malformed payloads,
  renames, concurrency, timeouts, uninitialized sessions).

## P1 — High-impact engineering
- [x] OpenCode read-before-write parity (shim ledger + session-scoped guard) —
  implemented + tested this session.
- [ ] #57 Recovery doc contradiction (`recovery.md` no-re-read vs enforced
  read-before-write) — doc fix + re-read-after-resume rule.
- [ ] #58 Reproducer identity binding (argv-to-contract like validators).
- [ ] #59 Shell-write freshness invalidation beyond enumerable redirects.
- [ ] #74 Rule-precedence audit: migrate checkable rules from skill prose to
  enforcement (Harness-IF: skill text is the lowest-precedence surface).
- [ ] #75 Scaffold-metric gaps: tokens-per-solve, time-to-solve, failure
  fingerprints in `metrics.py`.
- [ ] #76 Corpus contamination-hygiene infra (canaries, provenance registry, CI).
- [ ] #77 Hidden-test artifact hardening (private worktree root + scrub).
- [ ] #78 OpenCode completion-event gap (write/shell after-events for freshness).
- [ ] #80 `resolve-failure` re-arms without mandatory re-verify (F8).

## P2 — Experimental (feature-flagged)
- [ ] #60 Task-conditioned context scout (deterministic retrieval, token budgets).
- [ ] #61 Failure-guided debugging protocol (repro → hypotheses → discriminating
  experiments → minimal fix).
- [ ] #62 Adversarial verifier (boundary/property/differential checks in sandbox).
- [ ] #67 Bounded patch tournament for hard bugs (2–3 candidates, isolated worktrees).
- [ ] #63 Trace linter (repeat-action, thrash, stale-evidence detectors).
- [ ] #69 Offline harness optimizer (falsifiable contracts + human gate) — do not
  start before #63 lands.
- [ ] #71 Canonicalize paths at record time (`good first issue`).
- [ ] #79 Ablation execution matrix: 6 flash configs x 5 runs, one licensed
  task (needs declared model budget).
- [ ] #81 Weak-model progressive disclosure — evaluated on weak backends or dropped.

## Research / replication tasks
- [ ] #64 Harness-engineering literature verification pass (abstracts verified;
  full text open).
- [ ] #72 Competitor teardown with pinned commits (reuse arXiv:2609.00006 taxonomy).
- [ ] #73 Developer-report corpus (anecdotal/reproduced/corroborated).

## Host integration
- [ ] #65 OpenCode `tool.execute.after` payload audit across versions.
- [ ] #70 Antigravity/OpenCode lifecycle fixture corpus + stale-shim detection.

## Beginner-friendly
- [ ] #66 Seeded reproducible benchmark task (licensed repo + hidden validator).
- [ ] #71 Canonicalize paths at record time (replaces the cross-platform matrix item).
