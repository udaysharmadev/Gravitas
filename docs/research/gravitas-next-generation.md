# Gravitas Next-Generation Research Notes

Status: working notes. Abstract-level verification of all 8 arXiv entries +
2 non-arXiv sources completed (this session, via arXiv abs pages + repo +
OpenAI post). Full-text review is still open — do not cite beyond the
abstract-level facts recorded here until experiment sections are read.

## 1. Verified local findings (code + tests, HEAD `9fe0839`)

| # | Mechanism | What we confirmed | Gap it closes |
|---|-----------|-------------------|---------------|
| 1 | Schema-gated `cmd_report` **[verified local]** | `validate_episodes` without schema returned `[]` errors; crafted contradiction aggregated. Fixed + tested this session | Honesty gate (issue #27) |
| 2 | OpenCode read ledger **[verified local]** | Guard passed `reads=set()`; every existing-file edit denied. Shim now records reads per-session; guard enforces | Host parity F1 |
| 3 | Aggregate-skip in compare/metrics **[verified local]** | Raw glob + `KeyError` on stored aggregates. Fixed + tested | Bench robustness |
| 4 | Empty-report guard **[verified local]** | Empty input exited 0 with empty table. Now exit 1 | Anti-gaming |

## 2. Verified external findings (abstract-level; full text NOT yet reviewed)

- **Meta-Harness** (arXiv:2603.28052, Lee et al., 30 Mar 2026): outer loop over
  harness code; agentic proposer with filesystem access to prior candidates'
  source/scores/traces; +7.7pts text-classification at 4x fewer tokens; +4.7pts
  avg on 200 IMO problems across 5 held-out models; beats hand baselines on
  TerminalBench-2. Feeds the offline-optimizer design (#69): raw prior
  experience, not compressed feedback.
- **AHE** (arXiv:2604.25850, Lin et al., v4 18 May 2026): component/experience/
  decision observability; 10 iterations 69.7%->77.0% pass@1 Terminal-Bench 2,
  beats Codex-CLI 71.9%; transfers to SWE-bench-verified at 12% fewer tokens;
  **gains localize to tools/middleware/memory, NOT the system prompt**.
  Supports the deterministic-mechanism bias (#60, #61).
- **Adaptive Auto-Harness** (arXiv:2606.01770, Liu et al., v2 3 Jun 2026):
  evolution vs adaptation loss; harness tree + solve-time routing + human
  steering; a single densely-updated harness degrades on shifting streams.
  Supports routing over mutation + the human promotion gate (#69).
- **Source-code study** (arXiv:2609.00006, Barbaste et al., 15 Jul 2026):
  11 harnesses/~4M LOC incl. OpenCode — **no general agentic frameworks, no
  vector embeddings**; policy migrating prose->config; skills 9/11 vs MCP
  8/11. Validates the no-embedding default; host fixtures should pin
  config/skill surfaces (#65, #70).
- **Scaffold Effect** (arXiv:2607.22585, Vats & Golev, 8 Jun 2026,
  preliminary): harness choice -> up to **40x tokens/solved-task**; paired
  pass-rate diffs 0-8pp; failure fingerprints replicate across models.
  Supports paired under-budget reporting + the trace linter (#63).
- **Harness-Bench** (arXiv:2605.27922, Yao et al., v2 15 Oct 2026):
  106 sandboxed tasks, 5,194 trajectories; execution-alignment failures
  (reasoning decoupled from tool feedback/state/evidence/contracts); report at
  model-harness config level. Supports #61, #63 and bench methodology.
- **Harness-IF** (arXiv:2608.11727, Huang et al., 12 Aug 2026):
  Against-Prior Accuracy; all 12 models worse on against-prior rules
  (mean -5.81pp); precedence: system prompts, project files, user
  instructions **above** tool/skill descriptions. **Skill files are a
  low-precedence surface** — enforcement over prose; rules belong in project
  files where possible.
- **SWE-agent** (arXiv:2405.15793, Yang et al., v3 Nov 2024): ACI design drives
  behavior. Supports narrow file-edit ops + tool-feedback summaries.
- **OpenAI** ("Why SWE-bench Verified no longer measures frontier coding
  capabilities", Feb 2026, verified): 59.4% of audited tasks flawed (35.5%
  narrow, 18.8% wide) + verbatim gold-patch recall (contamination); recommends
  SWE-bench Pro. Direct input to the oracle audit in #66.
- **Agentless** (github.com/OpenAutoCoder/Agentless, 2.1k stars, MIT,
  verified): 3-phase localize->repair->validate, hierarchical fault
  localization, $0.34/issue on SWE-bench-lite. Shape mirrored in #60/#61/#67.

Rule (for the full-text pass in #64): for each paper record research question,
setup, finding, limitations, candidate Gravitas mechanism, existing equivalent,
cost, falsifiable experiment, and build/drop verdict. No paper counts until its
experiment section is read. Still unread: scaling agentic verifier (PMLR
v306), tool-augmented reasoning, search-based repair, test-time compute
allocation, differential/metamorphic testing, hierarchical retrieval, memory
compression, planning under uncertainty, model-router economics, prompt
injection vs agents, multi-agent vs single-agent empirical work.

## 3. Competitor implementation study (NOT STARTED — diffable surface planned)

Targets: SWE-agent, Agentless, gemini-cli, opencode, codex, OpenHands, aider
(execution loop, context construction, file tools, search, policy, memory,
retry, planning, tracing, patch/test selection, failure recovery). Pin commits
before comparing. Never claim a public repo exposes a proprietary model's
internal reasoning.

## 4. Developer-report corpus (NOT STARTED)

Collect Gemini/Claude-Code/weak-model failure reports (lost context, repeated
broken fix, wrong-file edits, dropped requirements, tool loops, quota burn,
parallel conflicts, compaction loss, green tests with broken behavior, false
"done", silent hooks, overaggressive policy). Label each anecdotal / reproduced
/ corroborated. Social-media consensus is not evidence.

## 5. What NOT to build (standing)

- Vector-DB / embedding retrieval as a default dependency (privacy, cost).
- Agent swarms without measured benefit per task family.
- Mandatory planning ceremony for trivial tasks.
- Self-modifying harness without human promotion gate.
- New overlapping frameworks where a scoped fix to an existing module suffices.
