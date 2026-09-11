# Troubleshooting

Common problems and solutions.

---

## 1. Installation Issues

### 1.1 Agent Doesn't Load GRAVITAS

**Symptom:** Agent behaves as if GRAVITAS isn't installed.

**Causes:**
1. SKILL.md not in the correct path
2. Agent doesn't support SKILL.md files
3. Agent needs restart to pick up new skill

**Diagnosis:**
```bash
# Check if file exists
ls ~/.agents/skills/gravitas/SKILL.md

# Check file content
head -5 ~/.agents/skills/gravitas/SKILL.md
```

**Fix:**
1. Ensure path is exactly: `~/.agents/skills/gravitas/SKILL.md`
2. Check agent documentation for SKILL.md support
3. Restart the agent completely

### 1.2 Agent Loads GRAVITAS But Doesn't Follow It

**Symptom:** Agent has access to GRAVITAS but doesn't exhibit expected behaviors.

**Causes:**
1. Agent's skill loading is disabled
2. Agent's context window is too small
3. Another skill is overriding GRAVITAS

**Fix:**
1. Enable skill loading in agent configuration
2. Increase context window if possible
3. Check for conflicting skills

---

## 2. Behavioral Issues

### 2.1 Agent Skips Reading Before Editing

**Symptom:** Agent edits files without reading them first.

**Cause:** Pillar 1 (Reconnaissance) not being followed.

**Diagnosis:**
- Check if agent is reading files before editing (look at tool calls)
- Check if agent is reading the target file specifically

**Fix:**
1. Ensure GRAVITAS is loaded
2. Add explicit instruction: "Read the file before editing it"
3. Check if agent is in a rush (Tier 0 fast path may skip formal recon)

### 2.2 Agent Claims Done Without Evidence

**Symptom:** Agent says "fixed" without running tests or verification.

**Cause:** Pillar 5 (Evidence) not being followed.

**Diagnosis:**
- Check if agent runs any verification commands
- Check if agent includes evidence in reports

**Fix:**
1. Ensure GRAVITAS is loaded
2. Add project-specific verification commands to `resources/verification-checklist.md`
3. Check if agent has access to test runners

### 2.3 Agent Doesn't Push Back

**Symptom:** Agent follows all requests without question.

**Cause:** Pillar 10 (Pushback) not being followed.

**Diagnosis:**
- Check if agent ever pushes back on any request
- Check if agent's pushback threshold is too high

**Fix:**
1. Ensure GRAVITAS is loaded
2. Lower pushback threshold
3. Add explicit instruction: "Push back once on harmful or ambiguous requests"

### 2.4 Agent Pushes Back Too Much

**Symptom:** Agent pushes back on obvious, harmless requests.

**Cause:** Pillar 10 (Pushback) is too aggressive.

**Diagnosis:**
- Check if agent pushes back on simple requests
- Check if agent's pushback threshold is too low

**Fix:**
1. Raise pushback threshold
2. Add explicit instruction: "Only push back on genuinely harmful or ambiguous requests"

### 2.5 Agent Is Too Verbose

**Symptom:** Agent reports too much detail for simple tasks.

**Cause:** GRAVITAS is applying full protocol to Tier 0 tasks.

**Diagnosis:**
- Check if agent is narrating process
- Check if agent is including unnecessary detail

**Fix:**
1. Use compressed checklists for Tier 0-1 tasks
2. Add explicit instruction: "For simple tasks, report only the outcome"
3. Reduce verbosity in reporting template

### 2.6 Agent Is Too Slow

**Symptom:** Agent takes too long to complete simple tasks.

**Cause:** GRAVITAS overhead is too high for the task.

**Diagnosis:**
- Check token usage per task
- Check time per phase

**Fix:**
1. Use tier-based loading (load only needed pillars)
2. Use compressed checklists
3. Consider model routing (use cheaper models for Tier 0-1)

---

## 3. Integration Issues

### 3.1 Browser Doesn't Work

**Symptom:** Browser subagent doesn't open or take screenshots.

**Cause:** Browser not available or not configured.

**Diagnosis:**
- Check if browser subagent is available
- Check if browser permissions are granted

**Fix:**
1. Ensure browser subagent is enabled
2. Grant browser permissions
3. Fall back to non-browser verification if unavailable

### 3.2 Artifacts Not Created

**Symptom:** `task.md` or `implementation_plan.md` not created.

**Cause:** Artifact creation not triggered.

**Diagnosis:**
- Check if task is Tier 2+ (artifacts only created for complex tasks)
- Check if artifact creation is enabled

**Fix:**
1. Ensure task is classified as Tier 2+
2. Enable artifact creation
3. Create artifacts manually if needed

### 3.3 Permission System Not Working

**Symptom:** Agent proceeds without permission for Tier 3+ actions.

**Cause:** Permission system not configured or bypassed.

**Diagnosis:**
- Check if permission system is enabled
- Check if agent is respecting tier classifications

**Fix:**
1. Enable permission system
2. Ensure agent respects tier classifications
3. Add explicit instruction: "Wait for user approval before Tier 3+ actions"

---

## 4. Performance Issues

### 4.1 Token Usage Too High

**Symptom:** Agent uses too many tokens per task.

**Cause:** Full protocol loaded for all tasks.

**Diagnosis:**
- Check token usage per task type
- Check which pillars are loaded

**Fix:**
1. Use tier-based loading
2. Use compressed checklists
3. Use skill scoping (load only needed modules)

### 4.2 Agent Too Slow

**Symptom:** Agent takes too long to complete tasks.

**Cause:** Too many verification steps or too much reading.

**Diagnosis:**
- Check time per phase
- Check number of files read

**Fix:**
1. Reduce verification steps for simple tasks
2. Use targeted grep instead of full file reads
3. Use recon caching to avoid re-reading files

---

## 5. Getting More Help

### 5.1 Self-Service

- Read the pillar deep specs: `resources/pillar-*.md`
- Check the edge cases: `docs/edge-cases.md`
- Review the eval framework: `eval/`

### 5.2 Community

- Open an issue on GitHub
- Search existing issues for similar problems
- Ask in discussions

### 5.3 Issue Template

When reporting an issue, include:

1. **Agent name and version**
2. **Operating system**
3. **GRAVITAS version**
4. **Task description**
5. **Expected behavior**
6. **Actual behavior**
7. **Tool call log** (if available)
8. **Token usage** (if available)

---

*This document is part of the GRAVITAS community and ecosystem phase. It provides troubleshooting guidance for common issues.*
