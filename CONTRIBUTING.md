# Contributing to GRAVITAS

GRAVITAS is a community-driven skill. Every contribution must follow
the GRAVITAS protocol — use it to contribute to it.

---

## Types of Contributions

### 1. Core Skill Improvements
Improving `skills/gravitas/SKILL.md`, agents, or resources.
**Tier 2** — high stakes, needs adversarial review.

### 2. Plugin Contributions
New plugins in `plugins/`. 
**Tier 1** — moderate, needs full verification.

### 3. Examples
New before/after examples in `examples/`.
**Tier 0-1** — low stakes.

### 4. Bug Reports
Issues with existing protocol or patterns.
**File an issue** with: what you expected, what happened, what task triggered it.

---

## Contribution Process

### Step 1: Pick your contribution

Check [open issues](../../issues) or propose your idea in a new issue first.
Tag it: `enhancement`, `plugin`, `example`, or `bug`.

### Step 2: Follow the protocol

Your contribution must follow GRAVITAS while building GRAVITAS:

```
□ Read the relevant existing files before editing
□ Plan your changes with risks documented
□ Test on 3+ real coding tasks (examples required for plugins)
□ Verify: all existing content still makes sense
□ Include VERDICT: PASS in your PR
```

### Step 3: File format

All skill files use YAML frontmatter + Markdown:

```markdown
---
name: [name]
description: [one-line description]
triggers:
  - [keyword1]
  - [keyword2]
---

# [Name]

[Content]
```

### Step 4: PR checklist

```markdown
## PR Checklist

- [ ] Follows GRAVITAS protocol (read → plan → implement → verify)
- [ ] 3+ real task examples tested (paste evidence or link to a session)
- [ ] No existing behavior broken or removed
- [ ] Frontmatter correct and complete
- [ ] VERDICT: PASS line included

VERDICT: PASS
[test evidence]
```

---

## Plugin Contribution Guide

A new plugin must have:

1. **`plugins/[name]/SKILL.md`** — the plugin file with frontmatter + content
2. **Entry in `plugins/README.md`** — add to the table
3. **3+ real examples** — paste in PR description or link to a session log

### Plugin structure

```markdown
---
name: gravitas-[domain]
description: > [multi-line description]
triggers:
  - [keyword]
---

# GRAVITAS — [Domain] Extension

Extends base GRAVITAS. Load `skills/gravitas/SKILL.md` first.

## [Domain] Recon Additions
## [Domain] Anti-Patterns  
## [Domain] Verification
## VERDICT for [Domain] Tasks
```

### Plugin quality bar

A plugin ships when it demonstrably improves output on 3+ real tasks.
Paste the before/after (with GRAVITAS base vs GRAVITAS + plugin) in the PR.

---

## Example Contribution Guide

Add to `examples/[task-type]/README.md`:

```markdown
# [Task Type] — Before vs After GRAVITAS

**Task:** [one sentence]

## ❌ Without GRAVITAS
[paste actual model output, warts and all]

**Problems:**
- [specific problem 1]
- [specific problem 2]

## ✅ With GRAVITAS
[paste actual GRAVITAS output — recon, plan, impl, evidence]

VERDICT: PASS
```

Real examples only. No fabricated "ideal" responses.

---

## Code of Conduct

1. Be precise. Vague feedback helps no one.
2. Be honest. If something doesn't work, say why.
3. Follow the protocol. Use GRAVITAS to contribute to GRAVITAS.
4. No preamble. Lead with the point.
