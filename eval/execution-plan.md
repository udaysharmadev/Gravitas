# Execution Plan

Step-by-step plan for executing the GRAVITAS evaluation suite.

---

## 1. Setup (Week 7-8)

### 1.1 Infrastructure Setup

| Task | Owner | Duration | Dependencies |
|------|-------|----------|-------------|
| Install GRAVITAS in test Antigravity workspace | Eval lead | 1 day | None |
| Prepare task repositories at specified commits | Eval lead | 2 days | None |
| Set up logging to capture all tool calls | Eval lead | 1 day | None |
| Configure token counting | Eval lead | 1 day | None |
| Set up scorer.py environment | Eval lead | 0.5 days | None |
| Verify all 25 tasks are runnable | Eval lead | 2 days | Repos ready |

### 1.2 Task Verification

For each of the 25 tasks:
1. Clone the repository at the specified commit.
2. Verify the task description matches the codebase state.
3. Verify the success criteria are achievable.
4. Verify the reference solution works.
5. Run the existing test suite to confirm it passes.

### 1.3 Rater Recruitment

| Task | Owner | Duration | Dependencies |
|------|-------|----------|-------------|
| Recruit 3 qualified raters | Eval lead | 1 week | None |
| Conduct rater training | Eval lead | 1 hour | Raters recruited |
| Run calibration session | Eval lead | 1 hour | Raters trained |

---

## 2. Execution (Week 8-10)

### 2.1 Condition A: Gemini Baseline

| Task | Duration | Notes |
|------|----------|-------|
| Run 25 tasks × 3 runs | 3 days | 15 min per task, sequential |
| Collect logs | Ongoing | Auto-collect during execution |
| Verify logs complete | 0.5 days | Check for missing data |

### 2.2 Condition B: Gemini + GRAVITAS

| Task | Duration | Notes |
|------|----------|-------|
| Install GRAVITAS skill | 0.5 days | Load into workspace |
| Run 25 tasks × 3 runs | 3 days | 15 min per task, sequential |
| Collect logs | Ongoing | Auto-collect during execution |
| Verify logs complete | 0.5 days | Check for missing data |

### 2.3 Condition C: Claude Baseline

| Task | Duration | Notes |
|------|----------|-------|
| Set up Claude Code environment | 1 day | Install and configure |
| Run 25 tasks × 3 runs | 3 days | 15 min per task, sequential |
| Collect logs | Ongoing | Auto-collect during execution |
| Verify logs complete | 0.5 days | Check for missing data |

### 2.4 Condition D: Claude + GRAVITAS

| Task | Duration | Notes |
|------|----------|-------|
| Install GRAVITAS skill | 0.5 days | Load into Claude Code |
| Run 25 tasks × 3 runs | 3 days | 15 min per task, sequential |
| Collect logs | Ongoing | Auto-collect during execution |
| Verify logs complete | 0.5 days | Check for missing data |

### 2.5 Execution Controls

| Control | Implementation |
|---------|---------------|
| Same tasks across conditions | Use task IDs from eval/tasks/ |
| Same repositories and commits | Pin commit hashes in task definitions |
| Temperature 0 | Set in model config where supported |
| Fresh sessions | New session for each task run |
| No cross-contamination | Execute conditions sequentially |

---

## 3. Scoring (Week 10)

### 3.1 Automated Scoring

| Task | Duration | Notes |
|------|----------|-------|
| Run scorer.py on all logs | 0.5 days | Compute automated metrics |
| Generate diff scoping ratios | Included | Requires reference diffs |
| Generate recon rates | Included | From tool call logs |
| Generate failure repetition rates | Included | From tool call logs |
| Generate token overhead | Included | From token counts |
| Generate task success rates | Included | From verification results |

### 3.2 Expert Review Scoring

| Task | Duration | Notes |
|------|----------|-------|
| Review false-completion claims | 2 days | Expert checks each claim |
| Review tier-adherence | 1 day | Expert checks ceremony |
| Review adversarial-catch | 1 day | Expert compares QA to implementation |
| Review pushback rate | 0.5 days | Expert identifies questionable requests |

### 3.3 Human Rating

| Task | Duration | Notes |
|------|----------|-------|
| Rate outcome-first-ness | 3 days | 3 raters × 25 responses |
| Calculate inter-rater reliability | 0.5 days | Cohen's kappa |
| Resolve disagreements | 0.5 days | Calibration session |
| Finalize ratings | 0.5 days | Consensus scores |

---

## 4. Analysis (Week 10)

### 4.1 Statistical Analysis

| Task | Duration | Notes |
|------|----------|-------|
| Mann-Whitney U tests | 0.5 days | Per metric, per comparison |
| Bootstrap confidence intervals | 0.5 days | 1000 iterations per metric |
| Effect size calculation | 0.5 days | Cohen's d, odds ratios |
| Multiple comparison correction | Included | Bonferroni |
| Per-pillar breakdowns | 0.5 days | Per metric, per pillar |

### 4.2 Visualization

| Task | Duration | Notes |
|------|----------|-------|
| Bar charts | 0.5 days | Metric comparison across conditions |
| Radar charts | 0.5 days | Multi-metric profile per condition |
| Scatter plots | 0.5 days | Token overhead vs. success rate |
| Heatmaps | 0.5 days | Per-task performance across conditions |

### 4.3 Report Writing

| Task | Duration | Notes |
|------|----------|-------|
| Executive summary | 0.5 days | Key findings and recommendations |
| Detailed results | 1 day | Per-metric, per-condition analysis |
| Per-pillar breakdowns | 0.5 days | Which pillars improved most |
| Recommendations | 0.5 days | What to optimize, what to keep |

---

## 5. Timeline Summary

| Week | Phase | Activities |
|------|-------|-----------|
| 7-8 | Setup | Infrastructure, task verification, rater recruitment |
| 8-9 | Execution | Conditions A and B (Gemini) |
| 9-10 | Execution | Conditions C and D (Claude) |
| 10 | Scoring | Automated, expert review, human rating |
| 10 | Analysis | Statistical analysis, visualization, reporting |

**Total duration:** 4 weeks
**Total estimated effort:** ~200 hours

---

## 6. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Model API changes during eval | Medium | High | Pin versions, run in compressed timeframe |
| Insufficient task diversity | Medium | Medium | 7 categories, 25 tasks |
| Rater fatigue | Medium | Medium | Limit to 20 tasks per rater, provide breaks |
| GRAVITAS token overhead too high | Low | High | Monitor during pilot, optimize if needed |
| Flaky tests in task repos | Medium | Medium | Pre-verify stability, exclude flaky tests |
| Scorer bugs | Low | Medium | Test on known data, manual verification |

---

## 7. Success Criteria Checklist

After analysis, check:

- [ ] B closes ≥70% of gap to C on false-completion rate
- [ ] B closes ≥70% of gap to C on diff-scoping ratio
- [ ] B matches or exceeds C on Gemini-favoring tasks
- [ ] B's token overhead is <3× baseline
- [ ] B improves over A on all metrics
- [ ] D improves over C on all metrics
- [ ] No metric regresses by >10% in any condition
- [ ] Inter-rater reliability kappa ≥ 0.6
- [ ] All 300 task runs completed
- [ ] All metrics computed and reported

---

*This execution plan is part of the GRAVITAS evaluation framework. It provides a detailed timeline and procedure for executing the evaluation.*
