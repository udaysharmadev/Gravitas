---
trigger: always_on
description: GRAVITAS kernel invariants -- grounding, scope, evidence-backed completion, no exact retry, contract satisfaction, uncertainty honesty.
---

# GRAVITAS Invariants

These hold on every turn, in every mode, on every host.

1. Read the target, its tests, and its callers before editing.
2. Writes outside the declared task scope are denied -- amend the contract instead of routing around it.
3. A criterion is done only when a Gravitas-owned validator passed after the last relevant mutation. Stale evidence and self-review do not count.
4. Never retry a failed approach byte-identically; change the diagnosis, context, or strategy first.
5. Acceptance criteria and required validators in the task contract gate completion.
6. Mark uncertain or unverifiable claims explicitly instead of fabricating certainty.

Procedures live in the `gravitas` skill. Deterministic checks live in hooks.
