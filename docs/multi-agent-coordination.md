# Multi-Agent Coordination

How GRAVITAS handles multiple agents working on the same codebase simultaneously.

---

## 1. Coordination Model

### 1.1 Agent Types

| Type | Role | Autonomy |
|------|------|----------|
| **Lead Agent** | Plans, coordinates, reports | Full |
| **Subagent** | Executes specific tasks | Task-scoped |
| **Reviewer** | Adversarial critique | Independent |

### 1.2 Communication

Agents communicate through:
1. **Shared artifacts** — `task.md`, `implementation_plan.md`
2. **Failure logs** — shared across agents
3. **Git state** — branch, commits, diff
4. **Explicit messages** — for coordination

---

## 2. Coordination Patterns

### 2.1 Parallel Execution

Multiple agents work on independent tasks simultaneously.

```
Lead Agent
├── Subagent A: Fix bug in auth.ts
├── Subagent B: Fix bug in user.ts
└── Subagent C: Add tests for auth.ts
```

**Rules:**
- Each subagent works on independent files
- No overlapping edits
- Lead agent coordinates conflicts

### 2.2 Sequential Execution

Agents work on dependent tasks in sequence.

```
Lead Agent
├── Subagent A: Migrate database schema
└── Subagent B: Update API to use new schema
```

**Rules:**
- Subagent B waits for Subagent A to complete
- Lead agent verifies A's output before B starts
- Failure in A stops B

### 2.3 Reviewer Pattern

Independent agent reviews another agent's work.

```
Lead Agent
├── Subagent A: Implement feature
└── Reviewer B: Adversarial critique of A's work
```

**Rules:**
- Reviewer B is independent of Subagent A
- Reviewer B has no knowledge of A's plan
- Reviewer B's critique is unbiased

---

## 3. Conflict Resolution

### 3.1 File Conflicts

**Situation:** Two agents want to edit the same file.

**Resolution:**
1. Lead agent detects conflict
2. Lead agent assigns file to one agent
3. Other agent works on different file
4. If both edits are necessary, merge manually

### 3.2 Plan Conflicts

**Situation:** Two agents have conflicting plans.

**Resolution:**
1. Lead agent reviews both plans
2. Lead agent merges or selects one
3. Affected agents are notified
4. Plans are updated in shared artifacts

### 3.3 Resource Conflicts

**Situation:** Two agents need the same resource (database, API, etc.).

**Resolution:**
1. Lead agent sequences access
2. Agents wait for resource availability
3. Lead agent monitors for deadlocks

---

## 4. Shared State

### 4.1 Failure Log

All agents share a single failure log:

```markdown
## Failed Approaches

### [Date] [Agent ID] [Approach]
**What was tried:** [description]
**What happened:** [result]
**Why it failed:** [root cause]
**Status:** ✅ Resolved / ⚠️ Known Issue / ❌ Still Failing
```

**Rules:**
- All agents check failure log before re-attempting
- All agents log failures immediately
- No agent repeats a failed approach

### 4.2 Task Board

Shared task board tracks progress:

```markdown
## Tasks

### [Task ID] [Description]
**Assigned to:** [Agent ID]
**Status:** Pending / In Progress / Blocked / Complete
**Depends on:** [Task IDs]
**Blocked by:** [Reason]
```

**Rules:**
- Lead agent maintains task board
- Agents update status when starting/completing tasks
- Blocked tasks are escalated to lead agent

### 4.3 Artifact Registry

Shared registry tracks artifacts:

```markdown
## Artifacts

### [Artifact Name] [Path]
**Created by:** [Agent ID]
**Last modified:** [Agent ID] [Timestamp]
**Lock status:** Unlocked / Locked by [Agent ID]
```

**Rules:**
- Agents lock artifacts before editing
- Agents unlock artifacts after editing
- Locked artifacts cannot be edited by other agents

---

## 5. Communication Protocol

### 5.1 Message Types

| Type | Purpose | Format |
|------|---------|--------|
| **Status Update** | Report progress | `[Agent ID]: [Status] [Task ID]` |
| **Blocker Report** | Report blocker | `[Agent ID]: BLOCKED [Task ID] [Reason]` |
| **Conflict Alert** | Report conflict | `[Agent ID]: CONFLICT [File] [Other Agent ID]` |
| **Request Help** | Request assistance | `[Agent ID]: HELP [Task ID] [What's needed]` |
| **Handoff** | Transfer task | `[Agent ID]: HANDOFF [Task ID] [To Agent ID]` |

### 5.2 Message Routing

Messages are routed through:
1. **Shared artifacts** — for persistent state
2. **Git commits** — for code changes
3. **Direct messages** — for urgent coordination

---

## 6. Scaling

### 6.1 Agent Limits

| Metric | Recommended Limit | Reason |
|--------|------------------|--------|
| Concurrent agents | 3-5 | Coordination overhead increases |
| Sequential agents | 10+ | No coordination needed |
| Total agents per session | 10+ | Context window limits |

### 6.2 Coordination Overhead

| Agents | Overhead | Recommendation |
|--------|----------|----------------|
| 1 | None | Optimal |
| 2 | Low | Recommended for complex tasks |
| 3-5 | Moderate | Use for large tasks |
| 6+ | High | Avoid unless necessary |

---

## 7. Failure Modes

### 7.1 Common Failure Modes

| Failure Mode | Description | Mitigation |
|-------------|-------------|------------|
| **Deadlock** | Agents waiting for each other | Lead agent detects and resolves |
| **Race condition** | Agents editing same file | File locking |
| **Communication loss** | Agent doesn't receive message | Persistent artifacts |
| **State inconsistency** | Agents have different views of state | Shared artifacts as source of truth |
| **Agent crash** | Agent stops responding | Lead agent detects and reassigns |

### 7.2 Recovery Procedures

| Failure | Recovery |
|---------|----------|
| Agent crash | Lead agent reassigns tasks |
| Deadlock | Lead agent breaks cycle |
| State inconsistency | Re-read shared artifacts |
| Communication loss | Retry with persistent artifacts |

---

## 8. Evaluation

### 8.1 Metrics

| Metric | Description |
|--------|-------------|
| **Coordination success rate** | % of multi-agent tasks completed successfully |
| **Conflict resolution rate** | % of conflicts resolved without manual intervention |
| **Communication latency** | Time between message send and receipt |
| **State consistency** | % of time agents agree on state |

### 8.2 Test Cases

| Test | Agents | Expected |
|------|--------|----------|
| Parallel bug fixes | 2 | Both complete without conflict |
| Sequential migration | 2 | Second waits for first |
| Review pattern | 2 | Independent review |
| Conflict scenario | 2 | Conflict detected and resolved |
| Agent crash | 2 | Tasks reassigned |

---

*This document is part of the GRAVITAS advanced research phase. It defines the multi-agent coordination model.*
