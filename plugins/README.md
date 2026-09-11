# Plugin System

Community extensions for GRAVITAS. Each plugin is a self-contained skill
that loads on top of the base GRAVITAS protocol.

---

## Available Plugins

| Plugin | Purpose | Load When |
|--------|---------|-----------|
| [gravitas-security](./gravitas-security/SKILL.md) | Deep security review mode | Working on auth, input, db, API |
| [gravitas-perf](./gravitas-perf/SKILL.md) | Performance analysis mode | Optimizing hot paths, benchmarking |
| [gravitas-typescript](../skills/gravitas-typescript/SKILL.md) | TypeScript patterns | Any TypeScript project |
| [gravitas-python](../skills/gravitas-python/SKILL.md) | Python patterns | Any Python project |

---

## How to Use a Plugin

Add to your `GEMINI.md` or `AGENTS.md`:

```
When executing coding tasks, follow GRAVITAS from skills/gravitas/SKILL.md.
For security-related tasks, also load plugins/gravitas-security/SKILL.md.
```

Or reference directly in your task:

```
Review this auth module for security issues.
Load: skills/gravitas/SKILL.md + plugins/gravitas-security/SKILL.md
```

---

## Build Your Own Plugin

A GRAVITAS plugin is any markdown file with YAML frontmatter:

```markdown
---
name: gravitas-[your-domain]
description: One-line description of what this plugin adds.
triggers:
  - keyword1
  - keyword2
---

# GRAVITAS — [Domain] Extension

Extends base GRAVITAS with [domain]-specific patterns.
Load `skills/gravitas/SKILL.md` first, then this file.

## [Domain] Recon Additions
[what to check beyond standard recon]

## [Domain] Verification
[additional checks beyond standard verify chain]

## [Domain] Anti-Patterns
[domain-specific anti-patterns]

## [Domain] Patterns
[domain-specific best practices]
```

### Plugin Rules
1. Plugins extend — never override — base GRAVITAS rules
2. All 5 core rules still apply
3. Tier classification still applies
4. VERDICT: PASS/FAIL still required
5. Plugins add recon, patterns, and verification — not new rule systems

### Submitting a Plugin

1. Create `plugins/gravitas-[name]/SKILL.md`
2. Test it on 3+ real tasks (include evidence in PR)
3. Add to the table in this README
4. PR with `VERDICT: PASS` in description

---

## Plugin Ideas (open for contribution)

- `gravitas-go` — Go-specific patterns (goroutines, channels, defer)
- `gravitas-rust` — Rust patterns (lifetimes, ownership, unsafe)
- `gravitas-react` — React patterns (hooks, state, effect cleanup)
- `gravitas-sql` — Schema migration and query optimization
- `gravitas-docker` — Container and orchestration patterns
- `gravitas-api` — REST/GraphQL API design patterns
- `gravitas-mobile` — React Native / Flutter patterns
- `gravitas-ml` — ML/AI model training and evaluation patterns
