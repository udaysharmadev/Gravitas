# Architecture

Gravitas has three layers:

1. `skills/gravitas/SKILL.md` is the small, cacheable policy kernel.
2. `plugins/gravitas-antigravity/` enforces contracts before tools, records evidence after tools, persists compact state, and gates completion.
3. `benchmarks/` validates complete episodes against repository outcomes.

Runtime data lives under `.gravitas/sessions/<task-id>/` and is never committed. The append-only ledgers are the source of truth; `state.json` and `coverage.json` are rebuildable caches used for low-token resumption. `impact_graph.py` derives caller, test, and configuration targets from changed files; PostInvocation stores those targets so a resumed task can verify its blast radius without rebuilding context.

Conditional investigator, verifier, and impact-auditor roles are optional. The default execution path is a single agent.
