# GRAVITAS production-readiness gates

Last reviewed: 2026-10-07 (release-candidate audit; see Definition of Done below).

| Gate | Status | Evidence / remaining boundary |
|---|---|---|
| Agent Skills format | PASS | Skill frontmatter validated in CI; OpenCode name/description rules tested. |
| Core project install | PASS | `gravitas init` scaffolds skills without clobbering; idempotence tested. |
| Native plugin packaging | PASS | `agy` 1.2.2 validates `dist/gravitas-antigravity` (2 skills, 3 agents, hooks); bundle drift checked in CI. |
| OpenCode adapter | PASS | Templates + shim + guard + init tested; capability differences documented. |
| Wheel/sdist install | PASS | Wheel ships 60+ runtime files; CI force-reinstalls and smokes `doctor`/`decide` outside any checkout. |
| Runtime unit tests | PASS | 159 tests: policy, action bypass/fuzz, context, verification, adapters, bench plumbing. |
| Live hook trajectory | PARTIAL | Fixture-pinned payloads and `agy plugin validate` pass; a production model trajectory remains outside install verification. |
| Benchmark corpus | PARTIAL | 30 specs, 10 lanes, solver-blind synthetic fixtures, holdout + ablations; licensed pinned repos and hidden real validators pending. |
| Comparative results | BLOCKED | No eligible paired production dataset. |
| Public performance claims | BLOCKED | Research-preview disclosures enforced by `check_readme_claims.py` + report publication gate. |

## Definition of Done audit (2026-10-07)

- Canonical structure unambiguous: PASS (`skills/` canonical, `dist/` generated, `adapters/` host templates, `docs/adr/` decisions).
- Main CI green: PASS (local gate mirrors every CI step; remote run pending push).
- Installed CLI works outside checkout: PASS (isolated-venv + CI smoke).
- Deprecated host assumptions removed: PASS (workflows migrated; schemas verified vs live docs 2026-10-07).
- Competitor-imitation positioning removed: PASS (sweep clean; claims guard extended).
- Small stable policy kernel: PASS (6 invariants; `decide()` records).
- Adaptive planning/verification: PASS (conditional levels; escalation planner).
- Repository/context intelligence: PASS (cached graph, ranked retrieval, summaries).
- Acceptance criteria with evidence state: PASS (6 states; deficit-driven).
- Reproduction-first debugging: PASS (`repro` pairs + UNVERIFIABLE path).
- Stale evidence cannot satisfy gates: PASS (freshness enforced in gate + coverage).
- Action policy beyond regex denylisting: PASS (tokenizer + capability levels + fuzz).
- Antigravity current surfaces: PASS (`agy plugin validate`; rules/ + skills).
- OpenCode genuinely supported: PASS (init/agents/permissions/shim tested vs 1.18.35).
- Recovery from durable state: PASS (`summarize`/`resume` carry full handoff).
- Real pinned tasks + hidden validators: PARTIAL (synthetic solver-blind fixtures; licensed repos pending).
- Component ablations possible: PASS (configs declared; runs pending provider access).
- Security limitations documented: PASS (`SECURITY.md` contract + tested threat model).
- Simple installation: PASS (`init` + wheel + quickstart).
- Documentation current: PASS (launch hierarchy; research archive bannered).
- Reproducible release artifacts: PARTIAL (wheel/sdist build in CI; no release tag cut here).
- Evidence-backed claims only: PASS (no marketing numbers; gates enforced in code).
