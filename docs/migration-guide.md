# Migration Guide

How to migrate from other protocols or no protocol to GRAVITAS.

---

## 1. From No Protocol

### 1.1 What Changes

| Before | After |
|--------|-------|
| Agent acts without reading | Agent reads before writing |
| Agent claims done without evidence | Agent verifies before claiming |
| Agent follows bad requests | Agent pushes back once |
| Agent narrates process | Agent reports outcomes |

### 1.2 Migration Steps

1. Copy SKILL.md to `~/.agents/skills/gravitas/SKILL.md`
2. Restart your agent
3. Give it a task and observe behavior
4. Compare behavior to the "What Changes" table

### 1.3 What to Expect

- Agent will be slightly slower (reading before writing)
- Agent will be more reliable (verifying before claiming)
- Agent will push back occasionally (on bad requests)
- Agent will report differently (outcomes, not process)

### 1.4 Rollback

If GRAVITAS doesn't work for you:
1. Delete `~/.agents/skills/gravitas/SKILL.md`
2. Restart your agent
3. Agent returns to pre-GRAVITAS behavior

---

## 2. From Other Protocols

### 2.1 Migrating from Custom Rules

If you have custom rules in your agent's configuration:

1. **Identify overlapping rules** — GRAVITAS may already cover them
2. **Identify unique rules** — keep them as agent-specific overrides
3. **Test for conflicts** — ensure custom rules don't contradict GRAVITAS
4. **Merge gradually** — start with GRAVITAS, add custom rules as needed

### 2.2 Migrating from Other SKILL.md Files

If you have other SKILL.md files:

1. **Check for conflicts** — do the protocols contradict each other?
2. **Prioritize** — which protocol takes precedence?
3. **Test** — run tasks and observe behavior
4. **Merge** — combine protocols if possible, or choose one

### 2.3 Common Conflicts

| Conflict | Resolution |
|----------|------------|
| Custom rules say "skip reading" vs. GRAVITAS says "read first" | GRAVITAS wins — reading is non-negotiable |
| Custom rules say "always proceed" vs. GRAVITAS says "push back" | Depends on context — pushback is for harmful requests only |
| Custom rules say "be concise" vs. GRAVITAS says "report outcomes" | Compatible — outcomes can be concise |

---

## 3. From Antigravity's Default Behavior

### 3.1 What Changes

| Default Antigravity | With GRAVITAS |
|---------------------|---------------|
| Reads when it feels like it | Always reads before writing |
| Plans sometimes | Plans for Tier 1+ tasks |
| Claims done sometimes | Always verifies before claiming |
| Follows instructions blindly | Pushes back once on harmful requests |
| Reports process | Reports outcomes |

### 3.2 Migration Steps

1. GRAVITAS is designed to work alongside Antigravity's existing features
2. No configuration changes needed — just add the SKILL.md file
3. Antigravity's skill discovery will load GRAVITAS automatically

### 3.3 What Stays the Same

- Antigravity's context loading
- Antigravity's tool selection
- Antigravity's permission system
- Antigravity's subagent spawning

---

## 4. From Claude Code

### 4.1 Key Differences

| Claude Code | GRAVITAS |
|-------------|----------|
| 200-line system prompt | Single SKILL.md file |
| Complex activation rules | Simple trigger words |
| Heavy token overhead | Optimized for token efficiency |
| Framework-specific | Framework-agnostic |

### 4.2 Migration Steps

1. Remove Claude Code's system prompt from your configuration
2. Copy GRAVITAS's SKILL.md to your agent's skill directory
3. Restart your agent
4. Test with a simple task

### 4.3 What to Keep from Claude Code

- Any project-specific rules you've added
- Any custom verification commands
- Any team-specific conventions

These can be added as agent-specific overrides alongside GRAVITAS.

---

## 5. From Cursor

### 5.1 Key Differences

| Cursor | GRAVITAS |
|--------|----------|
| IDE-integrated | File-based |
| Complex configuration | Single file |
| Heavy token overhead | Optimized for token efficiency |
| Framework-specific | Framework-agnostic |

### 5.2 Migration Steps

1. Remove Cursor's agent configuration
2. Copy GRAVITAS's SKILL.md to your agent's skill directory
3. Restart your agent
4. Test with a simple task

---

## 6. Validation

### 6.1 After Migration, Verify

1. **Reconnaissance:** Agent reads files before editing
2. **Planning:** Agent plans for complex tasks
3. **Evidence:** Agent verifies before claiming done
4. **Pushback:** Agent pushes back on bad requests
5. **Reporting:** Agent reports outcomes, not process

### 6.2 If Something's Wrong

1. Check the troubleshooting guide: `docs/troubleshooting.md`
2. Check the edge cases: `docs/edge-cases.md`
3. Open an issue on GitHub with details

---

*This document is part of the GRAVITAS community and ecosystem phase. It defines the migration path from other protocols.*
