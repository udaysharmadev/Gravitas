# ADR-0002: Model-agnostic positioning

Date: 2026-10-07 · Status: accepted

## Context

Public and internal text framed the product as "make Gemini behave like
Claude" (headline, skill description, plan/explore agents, benchmark metric
"Claude Gap Closure", eval success criteria). That framing ties product
identity to a competitor, cannot be verified, and contradicts the runtime
goal: help any model operate closer to its achievable capability.

## Decisions

1. Positioning: "open-source reliability runtime for coding agents ...
   adaptive context, evidence-backed execution, scoped actions, resumable
   state, deterministic completion gates." Gemini + Antigravity stay
   first-class targets; OpenCode becomes one. No imitation language.
2. Benchmark primary metric is within-model (treatment vs. baseline, same
   model). Cross-model reference deltas are exploratory, always published
   with exact revisions, CIs, and absolute metrics.
3. Competitor names remain only where scientifically neutral: benchmark
   matrices, dated routing-table snapshots (labeled as such), and the
   research-hypothesis list. `check_readme_claims.py` now also rejects
   "Claude-like", "like Claude", "forces Gemini", "competitive with Claude".
4. Unsupported specifics removed: "80% of bugs" statistics, fixed model
   version claims (2.5-era context sizes), "think for a long time"
   instructions. Replaced with proportionate-effort and re-validate guidance.

## Non-changes

`eval/` design docs keep their A/B/C/D matrices (demoted to exploratory
where they were primary). Historical artifacts (`benchmarks/reports/`,
`superseded/`) are left byte-identical. `CLAUDE.md` stays: host integration,
not product identity.
