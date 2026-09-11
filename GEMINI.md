# GRAVITAS — Antigravity Rules

When executing coding tasks, follow the GRAVITAS skill loaded from `skills/gravitas/SKILL.md`.

## Non-Negotiable (5 Rules Only)

1. **Read before write** — always recon target + related files before any edit
2. **Plan before act** — numbered plan for any task touching 2+ files
3. **Verify with proof** — run commands, cite actual output, never claim without evidence
4. **Push back once** — state the risk, then defer to user
5. **No rationalization** — never say "this should work", verify or admit you can't

## Tier Classification

| Tier | What | Protocol |
|------|------|----------|
| 0 | Trivial (read, search, comment) | Act immediately |
| 1 | Moderate (function edit, new file) | Think → plan → execute → verify |
| 2 | High-stakes (migration, auth, delete) | Full plan → critique → user checkpoint → execute → verify |

## Verification

Run these and cite the output:
- TypeScript: `tsc --noEmit && eslint . && vitest run`
- Python: `mypy . && ruff check . && pytest`
- Rust: `cargo check && cargo clippy && cargo test`
- Go: `go vet ./... && go test ./...`

## Output Format

```
## What Changed
[files, behavior]

## Evidence
[command output]

## Why
[rationale]
```

---

## Conditional Roles

Default to one agent. Load the investigator, verifier, or impact-auditor role
from `plugins/gravitas-antigravity/agents/` only when its condition in
`skills/gravitas/references/delegation.md` is met.

## Deep-Dive Resources

Load when complexity requires:
- `skills/gravitas/resources/anti-rationalization.md` — defense against shortcuts
- `skills/gravitas/resources/verification-engine.md` — proof-based verification
- `skills/gravitas/resources/memory-protocol.md` — cross-session context
- `skills/gravitas/resources/adversarial-critique.md` — attack your own plan
- `skills/gravitas/resources/tool-orchestration.md` — tool patterns
- `skills/gravitas/resources/gemini-native.md` — Gemini optimizations
