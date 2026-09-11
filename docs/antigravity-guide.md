# Antigravity Integration Guide

How GRAVITAS integrates with Antigravity's features, tools, and workflows. This guide covers skill activation, tool usage patterns, permission mapping, artifact integration, and multi-agent coordination.

---

## 1. Skill Discovery & Activation

### 1.1 How GRAVITAS Is Discovered

GRAVITAS is installed as a skill in the `.agents/skills/gravitas/` directory. Antigravity discovers skills by scanning:

```
.agents/skills/
  gravitas/
    SKILL.md              # Core protocol
    resources/            # Deep specs, playbooks, adaptations
    examples/             # Worked examples
    scripts/              # Verification scripts
```

The skill is activated when the user's request matches one of the trigger words in the skill's frontmatter:

```yaml
triggers:
  - "implement"
  - "refactor"
  - "fix"
  - "build"
  - "debug"
  - "migrate"
  - "deploy"
  - "create"
  - "add"
  - "change"
  - "update"
  - "remove"
  - "delete"
  - "write"
  - "generate"
  - "set up"
  - "configure"
  - "test"
  - "verify"
```

### 1.2 When GRAVITAS Is Loaded

GRAVITAS is loaded into the agent's context when a trigger matches. The full SKILL.md is injected as system context. The agent then follows the GRAVITAS protocol for the duration of the task.

**What gets loaded:**
- SKILL.md (core protocol, ~3000 tokens)
- Pillar deep specs are loaded on-demand from `resources/` when needed
- Task playbooks are loaded when a task type is identified
- Language adaptations are loaded based on the project's language

**What doesn't get loaded:**
- Examples (loaded only when the agent needs a reference)
- Scripts (loaded only when verification is needed)
- Full pillar specs (loaded only for complex tasks)

### 1.3 Skill Deactivation

GRAVITAS remains active for the duration of the session or until the user explicitly says "skip GRAVITAS" or "use default behavior." The skill can also be deactivated by the agent when the task is clearly Tier 0 (trivial) and the full protocol is unnecessary.

---

## 2. Tool Usage Patterns

### 2.1 The `@` File Reference

**What it does:** Pulls specific files into context without consuming a full `read` call.

**GRAVITAS usage:**
- **Pillar 1 (Recon):** Use `@` to pull in specific files during recon without loading entire directories.
- **Pillar 2 (Plan):** Use `@` to reference files mentioned in the plan.
- **Pillar 5 (Evidence):** Use `@` to pull in test files for verification.

**Pattern:**
```
User: "Fix the bug in src/api/handler.ts"
Agent: @src/api/handler.ts @src/api/types.ts @tests/handler.test.ts
```

**When to use `@` vs. `read`:**
- Use `@` when you need 1-3 specific files in context.
- Use `read` when you need to examine file content in detail (line numbers, exact content).
- Use `grep` when you need to find files by content pattern.

### 2.2 The `!` Command Execution

**What it does:** Runs shell commands directly.

**GRAVITAS usage:**
- **Pillar 5 (Evidence):** Use `!` to run verification commands: `!npm test`, `!cargo check`, `!ruff check`.
- **Pillar 1 (Recon):** Use `!` for recon commands: `!git log --oneline -10`, `!ls -la`, `!find . -name "*.test.*"`.
- **Pillar 3 (Tiering):** Use `!` cautiously — commands that change state are higher tier.

**Tier mapping for commands:**

| Command Type | Tier | Example |
|-------------|------|---------|
| Read-only | 0 | `!git status`, `!ls`, `!cat file` |
| Test/verify | 0 | `!npm test`, `!cargo check`, `!ruff check` |
| Build | 1 | `!npm run build`, `!cargo build` |
| Install | 1-2 | `!npm install` (reversible), `!apt install` (system) |
| Deploy | 3-4 | `!git push origin main`, `!docker deploy` |
| Delete | 2-4 | `!rm -rf` (irreversible), `!git clean` |

**Safety rules:**
- Never run `!rm -rf` without explicit user confirmation (Tier 4).
- Never run `!git push --force` without explicit user confirmation (Tier 4).
- Always quote file paths with spaces: `!cat "path with spaces/file.txt"`.
- Run read-only commands freely (Tier 0).

### 2.3 Browser Subagent

**What it does:** Opens a browser, navigates to URLs, takes screenshots, reads DOM.

**GRAVITAS usage:**
- **Pillar 5 (Evidence):** Use browser screenshots as visual verification for UI changes.
- **Pillar 9 (Native Strengths):** Lean into browser for visual verification when code review isn't sufficient.

**Integration pattern:**
```
Agent: [makes UI change]
Agent: !browser open http://localhost:3000
Agent: [takes screenshot]
Agent: [compares with expected state]
Agent: "Visual verification: UI change renders correctly."
```

**Limitations:**
- Browser subagent runs in an isolated profile — cannot access authenticated pages without setup.
- Browser may not wait for dynamic content (React/Vue) to render.
- Browser is slower than code review for non-visual changes.

**When NOT to use browser:**
- Code-only changes (no UI impact).
- When `re-read` is sufficient verification.
- When the page requires authentication that the browser can't provide.

### 2.4 `codebase_search`

**What it does:** Semantic search across the codebase.

**GRAVITAS usage:**
- **Pillar 1 (Recon):** Use for finding related code, understanding architecture, locating test files.
- **Pillar 4 (Diff Scoping):** Use to verify no unrelated files are affected.

**Pattern:**
```
Agent: codebase_search "session validation middleware"
Agent: [finds relevant files]
Agent: @src/middleware/session.ts @src/routes/protected.ts
```

**When to use `codebase_search` vs. `grep`:**
- Use `codebase_search` for semantic/conceptual searches ("session validation").
- Use `grep` for exact string searches ("formatDate").
- Use `glob` for filename pattern searches (`**/*.test.ts`).

### 2.5 `list_dir`

**What it does:** Lists directory contents.

**GRAVITAS usage:**
- **Pillar 1 (Recon):** Use to understand project structure before diving into files.

**Pattern:**
```
Agent: list_dir src/
Agent: [sees: api/, components/, utils/, types/]
Agent: list_dir src/api/
Agent: [sees: handler.ts, routes.ts, middleware/]
```

---

## 3. Permission Integration (Tier → Permission Mapping)

### 3.1 How Tiers Map to Antigravity Permissions

Antigravity's permission system uses action/target pairs with Deny/Ask/Allow settings. GRAVITAS tiers map to these permissions:

| GRAVITAS Tier | Antigravity Permission | Action |
|--------------|----------------------|--------|
| **Tier 0** | Auto-granted | Read-only commands, file reads, searches |
| **Tier 1** | Implicit (within task scope) | File edits, test runs, builds |
| **Tier 2** | Session-level checkpoint | Dependency installs, config changes, multi-file edits |
| **Tier 3** | Explicit user approval | Schema changes, auth modifications, production config |
| **Tier 4** | Explicit approval + dry run | Force-pushes, data deletion, security changes |

### 3.2 Permission Request Pattern

When a Tier 2+ action is needed, the agent should:

1. **Before the action:** Present the plan and request permission.
2. **During the action:** Execute only the approved scope.
3. **After the action:** Report what was done with evidence.

**Example (Tier 3 — database migration):**
```
Agent: "This is a Tier 3 action — database migration affecting production data.

Plan:
1. Add migration file: migrations/20260908_add_user_phone.sql
2. Run migration against staging
3. Verify with tests
4. Deploy to production

Risk: Migration adds a column. Rollback requires DROP COLUMN (data loss for new data).

Do you approve this plan?"
```

### 3.3 Turbo Markers

Antigravity supports `// turbo` comments to skip certain checks for read-only actions. GRAVITAS uses turbo markers for:

- Read-only browser actions (screenshots, DOM reading)
- Read-only commands (`git status`, `ls`, `cat`)
- Recon-only operations (grep, search, list)

**Pattern:**
```
!// turbo git log --oneline -10
```

**Rules:**
- Never use turbo for mutating actions (edits, deletes, pushes).
- Never use turbo for verification (tests should always run fully).
- Turbo is for read-only recon and information gathering.

---

## 4. Artifact Integration

### 4.1 Task Artifact (`task.md`)

**What it is:** A structured markdown file that tracks the current task's state.

**GRAVITAS usage:**
- **Pillar 8 (Session Memory):** Use `task.md` to persist task state across context windows.
- **Pillar 2 (Plan):** Store the plan in `task.md` for reference.

**Structure:**
```markdown
# Task: [title]

## Status
[NOT STARTED | IN PROGRESS | DONE | BLOCKED]

## Plan
1. [step] — Status: [pending/done]
2. [step] — Status: [pending/done]

## Failure Log
- [attempt]: [result] — Do not retry

## Evidence
- [verification command]: [result]

## Notes
[Any additional context]
```

**When to create `task.md`:**
- Tier 1+ tasks with 3+ plan steps.
- Tasks that span multiple sessions.
- Tasks with complex verification requirements.

### 4.2 Implementation Plan Artifact (`implementation_plan.md`)

**What it is:** A detailed plan with risk analysis, adversarial critique, and revision.

**GRAVITAS usage:**
- **Pillar 2 (Plan + Adversarial Critique):** Store the full plan with critique and revision.

**Structure:**
```markdown
# Implementation Plan: [title]

## Tier Classification
- Reversibility: [assessment]
- Scope: [assessment]
- Privilege: [assessment]
- Final tier: [0/1/2/3/4]

## Plan Steps
### Step 1: [description]
- Files: [list]
- Risk: [what could go wrong]
- Evidence: [how to verify]
- Reversibility: [how to undo]

### Step 2: [description]
...

## Adversarial Critique
### Weakest Assumption
[analysis]

### Most Likely to Break
[analysis]

### Edge Cases Not Covered
[analysis]

## Revised Plan
[changes based on critique]
```

**When to create `implementation_plan.md`:**
- Tier 2+ tasks.
- Tasks with 5+ plan steps.
- Tasks involving security, auth, or production systems.

### 4.3 Walkthrough Artifact (`walkthrough.md`)

**What it is:** A step-by-step explanation of what was done and why.

**GRAVITAS usage:**
- **Pillar 7 (Outcome-First Reporting):** Use for detailed reporting when the user asks for a walkthrough.

**Structure:**
```markdown
# Walkthrough: [title]

## What Changed
- [file:line] — [change description]

## Why Each Change Was Made
- [change] — Because [reason from plan step]

## Verification
- [command] — [result]

## What Was NOT Changed
- [list of related code that was deliberately left alone]
```

**When to create `walkthrough.md`:**
- When the user explicitly asks "walk me through what you did."
- For complex changes that benefit from detailed explanation.
- For Tier 2+ changes that need documentation.

---

## 5. Workflow Integration

### 5.1 Standard Task Flow

```
User request
  │
  ▼
[Trigger match] ──→ GRAVITAS loaded
  │
  ▼
[Pillar 1: Recon] ──→ Read files, detect conventions, assess tier
  │
  ▼
[Pillar 2: Plan] ──→ Numbered plan + adversarial critique + revision
  │
  ▼
[Pillar 3: Tier Check] ──→ Confirm tier, request permission if needed
  │
  ▼
[Pillar 4: Execute] ──→ Scoped diffs, each traceable to plan step
  │
  ▼
[Pillar 5: Verify] ──→ Run evidence commands, cite results
  │
  ▼
[Pillar 6: Self-QA] ──→ Adversarial pass, try to break it
  │
  ▼
[Pillar 7: Report] ──→ Outcome-first, evidence-cited, structured
  │
  ▼
[Pillar 8: Log] ──→ Log failures if any, update session notes
```

### 5.2 Tier-0 Fast Path

```
User request (trivial)
  │
  ▼
[Pillar 1: Quick Read] ──→ Read target file
  │
  ▼
[Pillar 4: Execute] ──→ Make the change
  │
  ▼
[Pillar 5: Quick Verify] ──→ Re-read to confirm edit landed
  │
  ▼
[Pillar 7: Brief Report] ──→ 1-2 sentence outcome
```

### 5.3 High-Stakes Flow (Tier 3-4)

```
User request (high-stakes)
  │
  ▼
[Pillar 1: Deep Recon] ──→ Full module tree, dependencies, CI, git history
  │
  ▼
[Pillar 2: Full Plan] ──→ 5-15 steps, full risk analysis, adversarial critique
  │
  ▼
[Pillar 3: Tier Confirmation] ──→ Axis-based classification, user confirmation
  │
  ▼
[Plan presented to user] ──→ User reviews and approves
  │
  ▼
[Pillar 4: Execute] ──→ Each step verified before next
  │
  ▼
[Pillar 5: Full Verify] ──→ All verification tools, complete evidence
  │
  ▼
[Pillar 6: Full QA] ──→ Input attacks, boundaries, security, concurrency
  │
  ▼
[Pillar 7: Full Report] ──→ Complete template with all sections
  │
  ▼
[Pillar 8: Log] ──→ Log all failures, patterns, lessons
```

### 5.4 Failure Recovery Flow

```
Verification fails
  │
  ▼
[Pillar 8: Log Failure] ──→ Record attempt, result, root cause
  │
  ▼
[Check Failure Log] ──→ Has this approach been tried before?
  │
  ├─ YES → Try different approach
  │
  └─ NO → Diagnose, plan fix, re-execute
  │
  ▼
[Pillar 5: Re-verify] ──→ Run verification again
  │
  ▼
[Still failing?] ──→ 3+ failures → stop and report
```

---

## 6. Multi-Agent Coordination

### 6.1 When Multiple Agents Are Used

Antigravity may spawn subagents for parallel work. GRAVITAS applies to each agent independently, but coordination is needed for:

- Shared files (two agents editing the same file)
- Dependencies (agent B's output is agent A's input)
- Verification (agent A's change may affect agent B's tests)

### 6.2 Coordination Rules

**Rule 1: Each agent follows GRAVITAS independently.**
Each subagent loads GRAVITAS and follows the protocol. No agent skips pillars because another agent is handling them.

**Rule 2: File locking is implicit.**
If agent A is editing `src/utils.ts`, agent B should not edit the same file simultaneously. Agents should coordinate file ownership before starting.

**Rule 3: Verification is shared.**
If agent A changes a function that agent B tests, agent B's verification includes agent A's change. Verification is not per-agent — it's per-codebase.

**Rule 4: Failure logs are shared.**
If agent A fails on an approach, agent B should know about it. Share failure logs across agents.

### 6.3 Subagent Pattern

```
Parent agent
  │
  ├─→ spawns subagent for task A
  │     ├─→ subagent loads GRAVITAS
  │     ├─→ subagent follows protocol
  │     └─→ subagent reports back
  │
  ├─→ spawns subagent for task B
  │     ├─→ subagent loads GRAVITAS
  │     ├─→ subagent follows protocol
  │     └─→ subagent reports back
  │
  ▼
Parent agent verifies combined result
```

### 6.4 Conflict Resolution

When two agents produce conflicting changes:

1. **Detect the conflict:** Git merge conflict or verification failure.
2. **Diagnose:** Which agent's change is correct? Are both correct but incompatible?
3. **Resolve:** Merge the changes, or revert one and re-plan.
4. **Verify:** Re-run verification after resolution.
5. **Log:** Record the conflict and resolution for future reference.

---

## 7. Context Management

### 7.1 Token Budget Awareness

GRAVITAS adds overhead to the agent's context. The protocol should be aware of token budget:

| Component | Approximate Tokens |
|-----------|-------------------|
| SKILL.md (core) | ~3,000 |
| Pillar deep spec (per pillar) | ~2,000-4,000 |
| Task playbook | ~1,500-3,000 |
| Language adaptation | ~1,000-2,000 |
| Plan + critique | ~1,000-3,000 |
| Report | ~500-1,000 |
| **Total for a Tier 2 task** | **~10,000-15,000** |

### 7.2 Lazy Loading

Pillar deep specs are loaded on-demand, not all at once:

- **Tier 0:** Load SKILL.md only (~3K tokens).
- **Tier 1:** Load SKILL.md + relevant playbook (~5K tokens).
- **Tier 2:** Load SKILL.md + relevant pillar specs + plan (~10K tokens).
- **Tier 3-4:** Load everything (~15K tokens).

### 7.3 Context Eviction

When context is full, prioritize:

1. **Keep:** Current file being edited, plan, failure log summary.
2. **Evict:** Recon details from completed steps, old verification output.
3. **Persist:** Write critical data to `task.md` before evicting.

---

## 8. Error Handling

### 8.1 Tool Unavailable

If a required tool (Browser, `codebase_search`, etc.) is unavailable:

1. Fall back to available tools (grep, read, edit).
2. Report the limitation: "Browser subagent not available. Using code review for verification."
3. Do not claim verification that wasn't performed.

### 8.2 Permission Denied

If Antigravity denies a permission:

1. Report the denial: "Permission denied for [action]."
2. Suggest alternatives: "You can run [command] manually."
3. Do not attempt to bypass the permission.

### 8.3 Context Overflow

If the context window is full:

1. Persist critical data to `task.md`.
2. Summarize what's in context.
3. If possible, continue with a focused context (only current files).
4. If not possible, report: "Context limit reached. Recommend starting a new session."

---

## 9. Configuration

### 9.1 Customizing GRAVITAS for Your Project

Users can customize GRAVITAS by modifying:

- **Triggers:** Add or remove trigger words in `SKILL.md` frontmatter.
- **Tier boundaries:** Adjust the tier thresholds in Pillar 3 for your team's risk tolerance.
- **Verification commands:** Update the verification tool mapping in Pillar 5 for your project's stack.
- **Playbooks:** Add task-type-specific playbooks in `resources/task-playbooks/`.
- **Language adaptations:** Add or modify language-specific guidance in `language-adaptations/`.

### 9.2 Disabling Pillars

If a pillar doesn't fit your workflow, it can be disabled by adding a note in the SKILL.md:

```markdown
## Pillar 9 — Native Strengths
**DISABLED:** Browser subagent not available in this environment.
```

Disabled pillars are skipped during the cognitive loop. The agent does not load or follow the disabled pillar's spec.

### 9.3 Environment-Specific Configuration

Different environments may need different configurations:

- **Local development:** Full GRAVITAS, all pillars active.
- **CI/CD:** GRAVITAS with reduced ceremony (Tier 0-1 only).
- **Production:** GRAVITAS with full ceremony (all tiers).

---

## 10. Troubleshooting

### 10.1 GRAVITAS Not Activating

**Symptom:** The agent doesn't follow the GRAVITAS protocol.

**Checklist:**
1. Is the skill installed in `.agents/skills/gravitas/`?
2. Does the user's request match a trigger word?
3. Is the SKILL.md frontmatter correct?
4. Is Antigravity discovering the skill?

### 10.2 GRAVITAS Too Slow

**Symptom:** Tasks take too long because of GRAVITAS overhead.

**Solutions:**
1. For Tier 0 tasks, the fast path should be used (skip planning/critique).
2. Lazy-load pillar specs — don't load all 10 at once.
3. Use compressed checklists instead of full specs for simple tasks.
4. Consider disabling pillars that don't apply to your workflow.

### 10.3 GRAVITAS Not Finding Files

**Symptom:** Recon can't find the relevant files.

**Solutions:**
1. Check that the file paths in the task description are correct.
2. Use `glob` and `grep` to search broadly.
3. Check for symlinks, monorepo structures, or nested packages.
4. Ask the user for clarification on file locations.

### 10.4 Verification Always Fails

**Symptom:** The verification step always reports failure.

**Solutions:**
1. Check if the verification tool is installed and configured.
2. Check if the test suite was passing before the change.
3. Check if the failure is pre-existing (unrelated to the change).
4. Run the verification tool manually to see the actual output.

---

*This guide is part of the GRAVITAS protocol's supporting documentation. It describes integration with Antigravity's specific features. For general GRAVITAS usage, see the SKILL.md core protocol.*
