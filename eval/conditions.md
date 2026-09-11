# Evaluation Conditions

Experimental conditions for the GRAVITAS evaluation suite. Defines what is held constant, what varies, and how conditions map to research questions.

---

## 1. Conditions

| Condition | Model | Harness | Skill | Research Question |
|-----------|-------|---------|-------|-------------------|
| **A: Gemini Baseline** | Gemini 3 Pro | Default Antigravity | None | What is Gemini's baseline performance without behavioral discipline? |
| **B: Gemini + GRAVITAS** | Gemini 3 Pro | Default Antigravity | GRAVITAS loaded | How much does GRAVITAS improve Gemini's performance? |
| **C: Claude Baseline** | Claude Sonnet/Opus | Claude Code default | None | What is Claude's baseline performance without behavioral discipline? |
| **D: Claude + GRAVITAS** | Claude Sonnet/Opus | Claude Code default | GRAVITAS loaded | How much does GRAVITAS improve Claude's performance? |

---

## 2. Primary Comparisons

### 2.1 GRAVITAS Effect (Within-Model)

**Comparison 1:** A vs. B (Gemini without vs. with GRAVITAS)
- Research question: Does GRAVITAS improve Gemini's performance?
- Expected: Significant improvement on discipline metrics (false-completion, diff-scoping, recon rate).

**Comparison 2:** C vs. D (Claude without vs. with GRAVITAS)
- Research question: Does GRAVITAS improve Claude's performance?
- Expected: Moderate improvement (Claude already has some built-in discipline).

### 2.2 Cross-Model Comparison

**Comparison 3:** A vs. C (Gemini baseline vs. Claude baseline)
- Research question: How do the models compare without behavioral discipline?
- Expected: Claude may outperform on discipline metrics; Gemini may outperform on some task types.

**Comparison 4:** B vs. D (Gemini + GRAVITAS vs. Claude + GRAVITAS)
- Research question: Does GRAVITAS equalize performance across models?
- Expected: GRAVITAS closes the gap on discipline metrics.

---

## 3. Controls

### 3.1 Held Constant Across All Conditions

| Factor | Value | Justification |
|--------|-------|---------------|
| Tasks | Same 25 tasks | Ensures fair comparison |
| Repositories | Same repos, same commits | Eliminates codebase variation |
| Temperature | 0.0 (where supported) | Maximizes reproducibility |
| Prompt templates | Same base prompts | Eliminates prompt variation |
| Evaluation criteria | Same rubrics | Ensures fair scoring |
| Time limits | 15 minutes per task | Prevents infinite loops |

### 3.2 Varied Across Conditions

| Factor | Variation | Purpose |
|--------|-----------|---------|
| Model | Gemini 3 Pro vs. Claude Sonnet/Opus | Test GRAVITAS across models |
| Skill | None vs. GRAVITAS loaded | Test GRAVITAS effect |
| Harness | Antigravity vs. Claude Code | Test GRAVITAS across harnesses |

### 3.3 Controls Not Applied (Accepted Limitations)

| Factor | Why Not Controlled | Impact |
|--------|-------------------|--------|
| Time of day | Model APIs may have variable latency | Minimal — latency doesn't affect quality |
| API version | Models are updated continuously | Acceptable — we test current versions |
| Context window | Different models have different limits | Acceptable — we test within each model's limits |

---

## 4. Blinding Protocol

### 4.1 Human Rater Blinding

- Raters do not know which condition produced each response.
- Responses are anonymized before rating (remove model names, harness indicators).
- Raters evaluate responses in random order.
- Raters do not see other raters' evaluations until all ratings are complete.

### 4.2 Rater Assignment

- 3 independent raters per response.
- Raters are assigned randomly from a pool of qualified evaluators.
- No rater evaluates more than 20% of responses from the same condition.

### 4.3 Inter-Rater Reliability

- Calculate Cohen's kappa for each metric.
- If kappa < 0.6, convene a calibration session.
- If kappa < 0.4 after calibration, exclude the metric from analysis.

---

## 5. Run Configuration

### 5.1 Per-Task Runs

| Parameter | Value |
|-----------|-------|
| Runs per task per condition | 3 |
| Total task runs | 25 tasks × 4 conditions × 3 runs = 300 |
| Time per task | 15 minutes max |
| Total estimated time | 300 × 15 min = 75 hours |

### 5.2 Execution Order

- Tasks are executed in random order within each condition.
- Conditions are executed in sequence (A, B, C, D) to avoid cross-contamination.
- Fresh session for each task run (no carryover between runs).

### 5.3 Data Collection

For each run, collect:
- All tool calls (tool, arguments, output, timestamp)
- All file changes (git diff)
- All agent messages
- Verification results
- Token counts (input, output)
- Total time

---

## 6. Success Criteria

### 6.1 Primary Success Criteria (v1)

1. **B closes ≥70% of the gap to C** on false-completion rate and diff-scoping ratio.
2. **B matches or exceeds C** on tasks favoring Gemini's native strengths.
3. **B's token overhead is <3× baseline.**

### 6.2 Secondary Success Criteria (v1)

1. **B improves over A** on all metrics (GRAVITAS helps Gemini).
2. **D improves over C** on all metrics (GRAVITAS helps Claude).
3. **No metric regresses by >10%** in any condition.

### 6.3 Stretch Goals (v1)

1. B matches C on task success rate (GRAVITAS makes Gemini competitive with Claude).
2. B's token overhead is <2× baseline.
3. D's token overhead is <1.5× baseline.

---

## 7. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Model API changes during eval | Medium | High | Pin model versions, run eval in compressed timeframe |
| Insufficient task diversity | Medium | Medium | Include 7 task categories, 25 tasks total |
| Rater fatigue | Medium | Medium | Limit to 20 tasks per rater, provide breaks |
| GRAVITAS token overhead too high | Low | High | Monitor overhead during pilot runs, optimize if needed |
| Flaky tests in task repos | Medium | Medium | Pre-verify test stability, exclude flaky tests |

---

*This document is part of the GRAVITAS evaluation framework. It defines the experimental conditions for Phase 4 and ensures reproducibility of results.*
