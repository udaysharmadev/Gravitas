# Antigravity Integration Map

A detailed mapping of how GRAVITAS pillars interact with Antigravity's features and toolset. For each feature: which pillars use it, integration points, permissions needed, and caveats.

---

## 1. Browser Subagent

### Features
- Navigate to URLs
- Take screenshots
- Read DOM content
- Interact with page elements

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 5 (Evidence)** | Visual verification for UI changes | Use screenshots as independent evidence. Compare before/after states. |
| **Pillar 9 (Native Strengths)** | Lean into browser for verification | Use browser when code review isn't sufficient for visual verification. |
| **Pillar 1 (Recon)** | DOM reading for recon | Use DOM inspection to understand page structure before UI changes. |

### Permission Required
- `execute_url(domain)` for target sites
- No special permissions for localhost/internal URLs

### Turbo Marker
- `// turbo` for read-only browser actions (screenshots, DOM reading)
- Do NOT turbo for interactive actions (clicking, typing)

### Caveats
- Browser subagent runs in an isolated profile — cannot access authenticated pages without explicit setup.
- Browser may not wait for dynamic content (React/Vue) to render fully.
- Browser is slower than code review for non-visual changes.
- Screenshots may not capture dynamic state (animations, hover effects).

### When to Use
- UI changes that need visual verification.
- Before/after comparison for CSS changes.
- DOM inspection for understanding page structure.

### When NOT to Use
- Code-only changes (no UI impact).
- When `re-read` is sufficient verification.
- When the page requires authentication that the browser can't provide.

---

## 2. Artifacts

### Features
- Structured markdown files persisted across sessions
- Types: task.md, implementation_plan.md, walkthrough.md

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 2 (Plan)** | Store implementation plans | Write plan to `implementation_plan.md` for Tier 2+ tasks. |
| **Pillar 7 (Reporting)** | Store walkthroughs | Write detailed walkthrough to `walkthrough.md` when user requests. |
| **Pillar 8 (Session Memory)** | Persist failure logs | Write failure notes to `task.md` or `GRAVITAS_FAILURES.md`. |
| **Pillar 8 (Session Memory)** | Persist task state | Write current task state to `task.md` for context management. |

### Permission Required
- Standard file write permissions

### Turbo Marker
- Not applicable (artifacts are explicit writes, not background operations)

### Caveats
- Artifacts consume tokens in context. Keep them concise.
- Artifacts may contain sensitive information — review before sharing.
- Artifacts are project-level — they persist across sessions.

### When to Use
- Tier 1+ tasks with 3+ plan steps.
- Tasks spanning multiple sessions.
- Complex verification requirements.
- User requests a walkthrough.

### When NOT to Use
- Tier 0 tasks (overhead exceeds benefit).
- Simple single-step tasks.
- When context is limited (artifacts add to context load).

---

## 3. Manager Surface

### Features
- Multi-agent orchestration
- Task delegation
- Progress tracking

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 3 (Tiering)** | Coordinate tier-appropriate ceremony | Ensure each subagent follows the appropriate tier protocol. |
| **Pillar 8 (Session Memory)** | Share failure logs across agents | Subagents should share failure logs to prevent repeated failures. |
| **Pillar 4 (Diff Scoping)** | Coordinate file ownership | Prevent two agents from editing the same file simultaneously. |

### Permission Required
- Standard agent spawning permissions

### Turbo Marker
- Not applicable

### Caveats
- Each subagent loads GRAVITAS independently.
- File locking is implicit — agents should coordinate before editing.
- Verification is shared — agent A's changes may affect agent B's tests.
- Failure logs should be shared across agents.

### When to Use
- Large tasks that benefit from parallel execution.
- Tasks with independent sub-components.
- Tasks requiring different expertise (frontend + backend).

### When NOT to Use
- Simple tasks that don't benefit from parallelism.
- Tasks with tight dependencies between sub-components.
- Tasks where file conflicts are likely.

---

## 4. Permission System

### Features
- Action/target permission pairs
- Deny/Ask/Allow settings
- Session-level and per-action permissions

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 3 (Tiering)** | Map tiers to permissions | Tier 0: auto-granted. Tier 1: implicit. Tier 2: session checkpoint. Tier 3: explicit approval. Tier 4: approval + dry run. |
| **Pillar 10 (Pushback)** | Enforce permission boundaries | Push back on attempts to bypass permission requirements. |

### Permission Mapping

| GRAVITAS Tier | Permission Model | Gate |
|--------------|-----------------|------|
| 0 | Auto-granted | None |
| 1 | Implicit (within task scope) | Verify step only |
| 2 | Session-level checkpoint | Confirm before executing Tier 2 sub-actions |
| 3 | Explicit user approval | User must approve plan before execution |
| 4 | Explicit approval + dry run | User approves plan, dry run succeeds, rollback plan exists |

### Turbo Marker
- Not applicable (permissions are system-level, not user-controlled)

### Caveats
- Permission system may not map perfectly to all GRAVITAS tiers.
- Some tiers may require custom permission rules.
- Permission denials should be reported, not bypassed.

### When to Use
- Always — permission integration is core to GRAVITAS tiering.

### When NOT to Use
- N/A — always applicable.

---

## 5. Terminal Sandboxing

### Features
- Sandboxed command execution
- Restricted file system access
- Command timeout limits

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 5 (Evidence)** | Run verification commands | Use sandboxed terminal for `npm test`, `cargo check`, etc. |
| **Pillar 1 (Recon)** | Run recon commands | Use sandboxed terminal for `git log`, `ls`, `find`, etc. |
| **Pillar 3 (Tiering)** | Restrict high-tier commands | Sandbox prevents accidental execution of dangerous commands. |

### Permission Required
- Standard terminal access (sandboxed by default)

### Turbo Marker
- `// turbo` for read-only commands (`git status`, `ls`, `cat`)
- Do NOT turbo for mutating commands (`rm`, `git push`, `docker deploy`)

### Caveats
- Sandboxing may prevent some legitimate commands (e.g., `apt install`).
- Command timeouts may interrupt long-running verification.
- Sandboxed environment may differ from production.

### When to Use
- Always — terminal is the primary tool for verification and recon.

### When NOT to Use
- N/A — always applicable.

---

## 6. Task Tracker (Experimental)

### Features
- Track task progress
- Mark tasks as complete
- Store task metadata

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 8 (Session Memory)** | Persist task state | Use task tracker to persist task state across context windows. |
| **Pillar 2 (Plan)** | Track plan progress | Use task tracker to mark plan steps as complete. |

### Permission Required
- Standard task tracker permissions

### Turbo Marker
- Not applicable

### Caveats
- Task tracker is experimental — may not be available in all environments.
- Task tracker state may not persist across sessions.
- Task tracker may not support all GRAVITAS metadata.

### When to Use
- When available and appropriate for the task.
- For complex tasks with many plan steps.

### When NOT to Use
- When task tracker is not available.
- For simple tasks (overhead exceeds benefit).

---

## 7. MCP Servers

### Features
- Model Context Protocol servers
- External tool integration
- Custom tool definitions

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 9 (Native Strengths)** | Extend tool capabilities | Use MCP servers to add custom verification tools, domain-specific recon tools. |
| **Pillar 5 (Evidence)** | Custom verification | MCP servers can provide domain-specific verification (e.g., API testing, database queries). |

### Permission Required
- MCP server installation and configuration permissions

### Turbo Marker
- Not applicable (MCP servers are external integrations)

### Caveats
- MCP servers are external — they may not follow GRAVITAS conventions.
- MCP server availability may vary across environments.
- MCP server output may need interpretation for GRAVITAS evidence.

### When to Use
- When standard tools are insufficient for verification.
- When domain-specific tools are needed (API testing, database queries, etc.).

### When NOT to Use
- When standard tools are sufficient.
- When MCP server availability is uncertain.

---

## 8. `@` File References

### Features
- Pull specific files into context
- Reference files without full read

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 1 (Recon)** | Pull files during recon | Use `@` to bring specific files into context for inspection. |
| **Pillar 2 (Plan)** | Reference files in plan | Use `@` to reference files mentioned in plan steps. |
| **Pillar 5 (Evidence)** | Pull test files for verification | Use `@` to bring test files into context for verification. |

### Permission Required
- Standard file read permissions

### Turbo Marker
- `// turbo` for read-only file references

### Caveats
- `@` references consume tokens in context.
- `@` does not read file content — it only references the file.
- For detailed inspection, use `read` instead of `@`.

### When to Use
- When you need 1-3 specific files in context.
- For quick references during recon and planning.

### When NOT to Use
- When you need detailed file content (use `read`).
- When you need to find files by pattern (use `glob` or `grep`).

---

## 9. `!` Command Execution

### Features
- Run shell commands directly
- Capture command output

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 5 (Evidence)** | Run verification commands | `!npm test`, `!cargo check`, `!ruff check` |
| **Pillar 1 (Recon)** | Run recon commands | `!git log`, `!ls`, `!find` |
| **Pillar 3 (Tiering)** | Restrict dangerous commands | Map command types to tiers. |

### Tier Mapping for Commands

| Command Type | Tier | Example |
|-------------|------|---------|
| Read-only | 0 | `!git status`, `!ls`, `!cat file` |
| Test/verify | 0 | `!npm test`, `!cargo check`, `!ruff check` |
| Build | 1 | `!npm run build`, `!cargo build` |
| Install | 1-2 | `!npm install` (reversible), `!apt install` (system) |
| Deploy | 3-4 | `!git push origin main`, `!docker deploy` |
| Delete | 2-4 | `!rm -rf` (irreversible), `!git clean` |

### Permission Required
- Standard terminal access

### Turbo Marker
- `// turbo` for read-only commands (`git status`, `ls`, `cat`)
- Do NOT turbo for mutating commands

### Caveats
- Commands may have side effects not captured in the output.
- Commands may timeout on long-running operations.
- Commands may fail silently (exit code 0 but wrong result).

### When to Use
- Always — commands are the primary tool for verification and recon.

### When NOT to Use
- N/A — always applicable.

---

## 10. Plan Mode

### Features
- Enter plan-only mode (no execution)
- Exit plan mode to execute
- Plan review and approval

### GRAVITAS Integration

| Pillar | Usage | Integration Point |
|--------|-------|-------------------|
| **Pillar 2 (Plan)** | Plan without execution | Use plan mode for Tier 2+ tasks where plan review is needed before execution. |
| **Pillar 3 (Tiering)** | User confirmation | Use plan mode to present plans for Tier 3-4 tasks. |

### Permission Required
- Standard plan mode permissions

### Turbo Marker
- Not applicable (plan mode is a mode, not a command)

### Caveats
- Plan mode may not be available in all environments.
- Plan mode may not support all GRAVITAS plan format requirements.
- Plan mode exit may require explicit user action.

### When to Use
- Tier 2+ tasks requiring user plan review.
- Complex tasks with 5+ plan steps.
- Tasks involving security, auth, or production systems.

### When NOT to Use
- Tier 0-1 tasks (overhead exceeds benefit).
- Simple tasks with clear solutions.

---

## Integration Priority Matrix

| Feature | Pillars Using It | Integration Complexity | Priority |
|---------|-----------------|----------------------|----------|
| `!` Command Execution | 1, 3, 5 | Low | High |
| `@` File References | 1, 2, 5 | Low | High |
| Terminal Sandboxing | 1, 3, 5 | Low | High |
| Browser Subagent | 1, 5, 9 | Medium | High |
| Artifacts | 2, 7, 8 | Medium | Medium |
| Permission System | 3, 10 | Medium | High |
| Plan Mode | 2, 3 | Low | Medium |
| Manager Surface | 3, 4, 8 | High | Medium |
| Task Tracker | 2, 8 | Low | Low |
| MCP Servers | 5, 9 | High | Low |

---

## Summary

GRAVITAS integrates with Antigravity through 10 primary features. The highest-priority integrations are:
1. **`!` Command Execution** — used by Pillars 1, 3, 5 for recon, tiering, and evidence.
2. **`@` File References** — used by Pillars 1, 2, 5 for recon, planning, and evidence.
3. **Permission System** — maps GRAVITAS tiers to Antigravity permissions.
4. **Browser Subagent** — used by Pillars 5, 9 for visual verification and native strengths.

The integration is designed to be non-intrusive: GRAVITAS uses Antigravity's existing features without requiring custom extensions or modifications.

---

*This integration map is part of the GRAVITAS protocol's research foundation. It documents how GRAVITAS interacts with Antigravity's specific features and informs the implementation of the integration guide (Phase 3.3).*
