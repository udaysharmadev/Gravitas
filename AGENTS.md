# GRAVITAS — Agent Rules

When executing coding tasks, follow the GRAVITAS skill loaded from `skills/gravitas/SKILL.md`.

## Non-Negotiable for Tier 1+ Tasks

1. **Read before writing** — always recon the target file and related context before any edit
2. **Plan before acting** — produce a numbered plan with failure modes before execution
3. **Verify before claiming done** — run verification commands and cite output
4. **Push back once on bad requests** — state the risk, then defer to user

## Verification Commands (adapt to your stack)

- TypeScript: `tsc --noEmit && eslint . && vitest run`
- Python: `mypy . && ruff check . && pytest`
- Rust: `cargo check && cargo clippy && cargo test`
- Go: `go vet ./... && go test ./...`
- Java: `javac . && spotbugs . && mvn test`
- C#: `dotnet build && dotnet test`
- Ruby: `ruby -c **/*.rb && rspec`
- PHP: `php -l **/*.php && phpunit`

## Tier Classification

| Tier | Reversibility | Protocol |
|------|--------------|----------|
| 0 | Trivial (read, search, comment) | Act immediately |
| 1 | Moderate (function edit, new file) | Plan → execute → verify |
| 2 | High-stakes (migration, auth, delete) | Full plan → critique → user checkpoint → execute → verify |

When uncertain, classify UP (treat as more cautious tier).

## Output Format

Every response leads with:
1. What changed (files, lines, behavior)
2. Evidence it works (test output, lint clean)
3. What needs user input (if anything)

---

## Project Structure

```
├── plugin.json                    # Antigravity plugin manifest
├── skills/gravitas/               # Portable skill (main location)
│   ├── SKILL.md                   # Core protocol (5 rules + tiers)
│   ├── PROMPT-TEMPLATE.md         # 3-layer assembly guide
│   ├── references/                # Progressive policy details
│   ├── resources/                 # Deep-dive specs (load on demand)
│   └── scripts/verify.sh          # VERDICT: PASS/FAIL
├── examples/                      # Before/after comparisons
├── benchmarks/                    # Evaluation framework
├── scripts/                       # Analysis tools
└── .agents/skills/gravitas/       # Antigravity compatibility
```

## Conditional Roles

The default is one agent. Load the investigator, verifier, or impact-auditor
role from `plugins/gravitas-antigravity/agents/` only when its spawn condition
in `skills/gravitas/references/delegation.md` is met.

## Deep-Dive Resources

Load when complexity requires:
- `resources/anti-rationalization.md` — defense against shortcuts
- `resources/verification-engine.md` — proof-based verification
- `resources/memory-protocol.md` — cross-session context
- `resources/adversarial-critique.md` — attack your own plan
- `resources/tool-orchestration.md` — tool patterns
- `resources/gemini-native.md` — Gemini optimizations
