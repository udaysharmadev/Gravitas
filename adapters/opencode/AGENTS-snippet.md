<!-- GRAVITAS-OPENCODE-START: managed by `gravitas init --host opencode`. Edit inside freely; reruns preserve this block. -->

## GRAVITAS Invariants

1. Read the target, its tests, and its callers before editing.
2. Writes outside the declared task scope are denied -- amend the contract, not the route.
3. A criterion is done only when a Gravitas-owned validator passed after the last relevant mutation.
4. Never retry a failed approach byte-identically; change something first.
5. Acceptance criteria and required validators gate completion.
6. Mark unverifiable claims explicitly.

Load the `gravitas` skill for procedures (`/gravitas` or automatic discovery).
Use `gravitas validator` / `gravitas repro` / `gravitas summarize` for evidence.
High-stakes changes (migrations, deletions, auth, production config): load `gravitas-highstakes` first.

<!-- GRAVITAS-OPENCODE-END -->
