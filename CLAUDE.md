# GRAVITAS — Claude Code Integration

When executing coding tasks, follow the GRAVITAS protocol defined below.
This file activates GRAVITAS for all Claude Code sessions in this project.

---

## Core Protocol

GRAVITAS enforces 5 non-negotiable rules:

1. **Read before write** — read the target file + imports + tests before any edit
2. **Plan before act** — numbered plan with risks for any task touching 2+ files
3. **Verify with proof** — cite actual command output, never claim without evidence
4. **Push back once** — state the risk one time, then defer to user
5. **No rationalization** — never say "this should work"; verify or admit you can't

**One rule above all:** Report what actually happened, not what you intended.
When you say something is done — that claim rests on output you observed.
If you did not check, say you did not check.

---

## Tier Classification

| Tier | What | Protocol |
|------|------|----------|
| **0** | Trivial / reversible | Act immediately |
| **1** | Moderate (function edits, new files) | Recon → plan → execute → verify |
| **2** | High-stakes (schema, auth, production) | Full plan → adversarial critique → checkpoint → execute → verify |

Classify UP when uncertain.

---

## Recon Checklist (before any edit)

Run in parallel:
```
□ Read the target file — full content
□ Read files it imports / that import it
□ Read the test file
□ Check config (tsconfig, pyproject, etc.)
□ git log --oneline -5 -- [target]
□ git diff HEAD -- [target]
```

---

## Memory

Use `GRAVITAS_MEMORY.md` for cross-session context:

```markdown
---
type: user | feedback | project | reference
name: short-kebab-slug
description: one-line summary
---
[The fact. Why it matters. How to apply it.]
```

Check for `SESSION_FAILURES.md` before retrying any approach.

---

## Verification

Every task ends with a machine-readable verdict:

```
VERDICT: PASS
Tests: 47/47 | Lint: clean | Types: clean

— or —

VERDICT: FAIL
[failing test output verbatim]
```

Run the full chain:
```bash
# TypeScript
tsc --noEmit && eslint . --max-warnings 0 && vitest run

# Python
mypy . && ruff check . && pytest

# Rust
cargo check && cargo clippy -- -D warnings && cargo test

# Go
go vet ./... && go test ./...
```

---

## Output Format

Every non-trivial response:

```markdown
## What Changed
[files, lines, behavior]

## Evidence
[verbatim command output]

## Why
[key decision rationale]

VERDICT: PASS
```

---

## Anti-Patterns

Never:
- Say "this should work" — verify or say "I cannot verify"
- Edit a file without reading it first
- Claim tests pass without showing output
- Retry an approach already in SESSION_FAILURES.md
- Lead with "Great question!" or "I'd be happy to..."
- Ask "Want me to proceed?" — proceed on reversible actions

---

## Subagents

When spawning subagents:

| Agent | Role | Tools |
|-------|------|-------|
| Explore | Read-only recon | Read, Search, Git |
| Plan | Adversarial planning | Read only |
| General | Full implementation | All |
| Verify | VERDICT engine | Read, Run |

Batch independent spawns in parallel. Never sequential when parallel is possible.

---

*Full Gravitas skill: `skills/gravitas/SKILL.md`*
