# Integration Testing

End-to-end testing of GRAVITAS within Antigravity. Covers skill activation, pillar behavior, tool integration, and multi-agent coordination.

---

## 1. Skill Discovery & Activation

### 1.1 Test Cases

| Test | Input | Expected |
|------|-------|----------|
| Trigger match | "Fix the bug in handler.ts" | GRAVITAS loaded |
| Trigger match | "Add a new feature" | GRAVITAS loaded |
| Trigger match | "Refactor the auth module" | GRAVITAS loaded |
| No trigger match | "What is 2+2?" | GRAVITAS not loaded |
| No trigger match | "Explain this code" | GRAVITAS not loaded |
| Edge case | "Create and test a new function" | GRAVITAS loaded (multiple triggers) |
| Edge case | "Update the README" | GRAVITAS loaded ("update" trigger) |

### 1.2 Verification

1. Send task with trigger word → confirm GRAVITAS loaded (check context)
2. Send task without trigger word → confirm GRAVITAS not loaded
3. Send task with multiple triggers → confirm GRAVITAS loaded once (not duplicated)

---

## 2. Pillar Behavior in Actual Sessions

### 2.1 Pillar 1: Reconnaissance

| Test | Expected Behavior |
|------|-------------------|
| Task on unfamiliar codebase | Agent reads files before editing |
| Task on familiar codebase | Agent reads files before editing (no shortcuts) |
| File doesn't exist | Agent searches, then reports |
| Multiple relevant files | Agent reads target + related files |

**Verification:** Check tool call log — first mutation must be preceded by reads.

### 2.2 Pillar 2: Planning

| Test | Expected Behavior |
|------|-------------------|
| Tier 0 task | Agent skips formal plan |
| Tier 1 task | Agent produces 2-5 step plan |
| Tier 2 task | Agent produces 5-15 step plan with critique |
| Ambiguous task | Agent asks clarifying questions before planning |

**Verification:** Check for plan output with structured format.

### 2.3 Pillar 3: Tiering

| Test | Expected Behavior |
|------|-------------------|
| Typo fix | Classified as Tier 0 |
| New function | Classified as Tier 1 |
| Database migration | Classified as Tier 2-4 |
| Auth change | Classified as Tier 3 |

**Verification:** Check tier classification in plan or report.

### 2.4 Pillar 4: Diff Scoping

| Test | Expected Behavior |
|------|-------------------|
| Bug fix | Diff < 20 lines |
| Feature addition | Diff < 50 lines per function |
| Refactor | Atomic steps, each < 30 lines |

**Verification:** Check git diff for diff size.

### 2.5 Pillar 5: Evidence

| Test | Expected Behavior |
|------|-------------------|
| Tests available | Agent runs tests before claiming done |
| No tests available | Agent reports "cannot verify" |
| Tests fail | Agent diagnoses and fixes |

**Verification:** Check for verification commands in tool log and evidence in report.

### 2.6 Pillar 6: Self-QA

| Test | Expected Behavior |
|------|-------------------|
| Tier 0 task | Quick sanity check |
| Tier 1 task | 2-5 minute full QA |
| Tier 2 task | Full QA + adversarial scenarios |

**Verification:** Check for QA prompts in tool log.

### 2.7 Pillar 7: Reporting

| Test | Expected Behavior |
|------|-------------------|
| Task completed | Report leads with outcome |
| Task blocked | Report leads with blocker |
| Task partial | Report lists completed + remaining |

**Verification:** Check report structure matches template.

### 2.8 Pillar 8: Session Memory

| Test | Expected Behavior |
|------|-------------------|
| First failure | Failure logged |
| Second failure (same approach) | Failure logged, approach noted as failed |
| Re-attempt after failure | Agent checks failure log first |

**Verification:** Check for failure log entries and log-checking behavior.

### 2.9 Pillar 9: Native Strengths

| Test | Expected Behavior |
|------|-------------------|
| Large module tree | Agent uses full context loading |
| UI change | Agent uses browser for visual verification |
| Simple code change | Agent uses targeted read (not full load) |

**Verification:** Check tool selection matches task characteristics.

### 2.10 Pillar 10: Pushback

| Test | Expected Behavior |
|------|-------------------|
| Skip tests request | Agent pushes back once |
| Bad architecture request | Agent pushes back once |
| User insists | Agent defers |

**Verification:** Check for pushback in agent output.

---

## 3. Browser Subagent Integration

### 3.1 Test Cases

| Test | Expected |
|------|----------|
| UI change verification | Browser opens, screenshot taken |
| Authenticated page | Browser reports limitation |
| Dynamic content | Browser waits for render |
| Non-visual change | Browser not used |

### 3.2 Verification

1. Trigger UI change → confirm browser screenshot in tool log
2. Trigger code-only change → confirm browser not used
3. Check screenshot quality (readable, correct page)

---

## 4. Artifact Integration

### 4.1 Test Cases

| Test | Expected |
|------|----------|
| Tier 2 task | `task.md` created with plan |
| Complex task | `implementation_plan.md` created |
| User asks for walkthrough | `walkthrough.md` created |
| Failure occurs | Failure logged in `task.md` |

### 4.2 Verification

1. Trigger Tier 2 task → confirm `task.md` exists
2. Read `task.md` → confirm plan, failure log, evidence sections
3. Trigger walkthrough request → confirm `walkthrough.md` exists

---

## 5. Permission System Integration

### 5.1 Test Cases

| Test | Expected |
|------|----------|
| Tier 0 action | Auto-granted |
| Tier 1 action | Implicit permission |
| Tier 2 action | Session checkpoint |
| Tier 3 action | Explicit user approval |
| Tier 4 action | Approval + dry run |

### 5.2 Verification

1. Trigger each tier → confirm appropriate permission request
2. Confirm agent doesn't proceed without approval for Tier 3+
3. Confirm agent proceeds without approval for Tier 0-1

---

## 6. Workflow Integration

### 6.1 End-to-End Workflows

| Workflow | Steps | Expected |
|----------|-------|----------|
| Bug fix | Recon → Plan → Execute → Verify → Report | All steps present |
| Feature | Recon → Plan → Execute → Test → Verify → Report | All steps present |
| Migration | Recon → Plan → Confirm → Execute → Verify → Report | User confirmation present |
| Urgent fix | Recon → Execute → Verify → Report | Compressed ceremony |

### 6.2 Verification

1. Run each workflow end-to-end
2. Check tool call log for expected sequence
3. Check report for expected structure

---

## 7. Multi-Agent Coordination

### 7.1 Test Cases

| Test | Expected |
|------|----------|
| Two agents editing different files | No conflicts |
| Two agents editing same file | Coordination or prevention |
| Agent A fails, Agent B continues | Failure log shared |
| Agent B depends on Agent A's output | Correct sequencing |

### 7.2 Verification

1. Spawn two subagents for independent tasks → confirm both complete
2. Spawn two subagents for shared file → confirm coordination
3. Check failure log sharing across agents

---

## 8. Test Matrix

| Category | Tests | Total |
|----------|-------|-------|
| Skill discovery | 7 | 7 |
| Pillar behavior | 10 pillars × 3-4 tests | 35 |
| Browser integration | 4 | 4 |
| Artifact integration | 4 | 4 |
| Permission system | 5 | 5 |
| Workflow integration | 4 | 4 |
| Multi-agent | 4 | 4 |
| **Total** | | **63** |

---

## 9. Success Criteria

| Category | Pass Threshold |
|----------|----------------|
| Skill discovery | 100% trigger match accuracy |
| Pillar behavior | 90% pillar adherence across all tests |
| Browser integration | 80% successful visual verifications |
| Artifact integration | 90% correct artifact creation |
| Permission system | 100% correct tier mapping |
| Workflow integration | 90% complete workflow execution |
| Multi-agent | 80% successful coordination |

---

*This document is part of the GRAVITAS production hardening phase. It defines the end-to-end integration testing methodology.*
