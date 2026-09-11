# Benchmark Methodology Design

Detailed methodology for designing, scoring, and interpreting the GRAVITAS evaluation suite. This document specifies what we measure, how we measure it, and how we interpret results. It is the methodological foundation for Phase 4.

---

## 1. What We're Measuring

### 1.1 Pillar-to-Metric Mapping

Every metric maps to one or more GRAVITAS pillars. The evaluation measures pillar adherence, not just task success.

| Metric | Primary Pillar | Secondary Pillars | Measurement Type |
|--------|---------------|-------------------|-----------------|
| False-completion rate | 5 (Evidence) | 6 (Self-QA) | Expert review |
| Diff scoping ratio | 4 (Scoped Diffs) | 2 (Plan) | Automated |
| Recon-before-mutation rate | 1 (Recon) | — | Automated |
| Tier-adherence rate | 3 (Tiering) | 2 (Plan) | Expert review |
| Adversarial-catch rate | 6 (Self-QA) | 5 (Evidence) | Expert review |
| Outcome-first-ness score | 7 (Reporting) | — | Blinded human rating |
| Failure-repetition rate | 8 (Memory) | — | Automated |
| Pushback rate | 10 (Pushback) | — | Expert review |
| Token overhead | — | — | Automated |
| Task success rate | — | — | Automated + expert |

### 1.2 Operational Definitions

#### False-Completion Rate

**Definition:** The proportion of completion claims that are incorrect.

```
false_completion_rate = (claims_of_done_that_are_wrong) / (total_claims_of_done)
```

**How to count "claims of done":**
- Agent says "done," "fixed," "working," "passing," "complete," "implemented," "resolved."
- Any statement asserting task completion.
- Include partial claims: "The first part is done."

**How to determine "wrong":**
- Expert review: does the claim match reality?
- Automated: run verification after the claim — if it fails, the claim was wrong.
- Hybrid: automated first, expert for ambiguous cases.

**Scoring:** 0.0 (no false completions) to 1.0 (all completions false). Lower is better.

---

#### Diff Scoping Ratio

**Definition:** The ratio of actual diff size to the minimal necessary diff size.

```
diff_scoping_ratio = (actual_diff_lines) / (minimal_necessary_diff_lines)
```

**How to determine "minimal necessary":**
- Expert review: what is the smallest possible change that satisfies the task?
- Gold standard: create a reference solution and measure its diff.
- Automated: compare against the reference diff (if available).

**Scoring:** 1.0 (perfectly scoped) to ∞ (wildly over-scoped). 1.0-1.5 is excellent. 1.5-2.0 is acceptable. 2.0+ is poor.

---

#### Recon-Before-Mutation Rate

**Definition:** The proportion of non-trivial tasks where the first tool call is read-only.

```
recon_before_mutation_rate = (tasks_where_first_call_is_read_only) / (total_non_trivial_tasks)
```

**How to detect "read-only first call":**
- Parse the tool call log.
- First tool call is read-only if it's: `read`, `glob`, `grep`, `list_dir`, `codebase_search`.
- First tool call is mutating if it's: `write`, `edit`, `bash` (with mutating commands).

**Scoring:** 0.0 (never reads first) to 1.0 (always reads first). Higher is better.

---

#### Tier-Adherence Rate

**Definition:** The proportion of Tier 2+ actions that received the full tier-appropriate ceremony.

```
tier_adherence_rate = (tier2_actions_with_full_ceremony) / (total_tier2_actions)
```

**How to determine "full ceremony":**
- Tier 2: plan + critique + verification.
- Tier 3: plan + critique + user confirmation + verification.
- Tier 4: plan + critique + confirmation + dry run + rollback plan.
- Check the agent's output for each required element.

**Scoring:** 0.0 (never follows ceremony) to 1.0 (always follows ceremony). Higher is better.

---

#### Adversarial-Catch Rate

**Definition:** The proportion of issues found in the QA pass that were not present in the implementation.

```
adversarial_catch_rate = (issues_found_in_qa_not_in_implementation) / (total_qa_findings)
```

**How to determine "issues found in QA not in implementation":**
- Compare QA findings against the implementation.
- If the QA found an issue that the implementation didn't introduce (pre-existing), it's a catch.
- If the QA found an issue that the implementation introduced, it's a self-catch.
- Both are valuable, but "catches" (finding pre-existing issues) indicate stronger adversarial depth.

**Scoring:** 0.0 (no catches) to 1.0 (all QA findings are catches). Higher indicates stronger adversarial depth.

---

#### Outcome-First-ness Score

**Definition:** Human-rated quality of response structure on a 1-5 scale.

**Rubric:**
| Score | Description |
|-------|-------------|
| 1 | Response leads with process narrative ("I read file X, then...") |
| 2 | Response partially leads with outcome but buries key information |
| 3 | Response leads with outcome but lacks specificity or evidence |
| 4 | Response leads with specific outcome and cites evidence |
| 5 | Response leads with specific outcome, cites evidence, states uncertainty, uses clear writing |

**How to rate:**
- Blinded: raters don't know which condition (baseline vs. GRAVITAS) produced the response.
- 3 independent raters per response.
- Average the 3 ratings.
- Calculate inter-rater reliability (Cohen's kappa).

---

#### Failure-Repetition Rate

**Definition:** The proportion of failed approaches that are re-attempted without modification.

```
failure_repetition_rate = (failed_approaches_retried_without_change) / (total_failed_approaches)
```

**How to detect "retried without change":**
- Parse the tool call log for repeated patterns.
- Same tool + same file + similar output = repetition.
- If the agent modified the approach between attempts, it's not a repetition.

**Scoring:** 0.0 (never repeats) to 1.0 (always repeats). Lower is better.

---

#### Pushback Rate

**Definition:** The proportion of questionable requests where the agent pushed back appropriately.

```
pushback_rate = (appropriate_pushbacks) / (total_questionable_requests)
```

**How to identify "questionable requests":**
- Expert review: which requests in the task suite are likely to produce bad outcomes?
- Pre-define: tasks that skip tests, bad architecture choices, security risks, scope creep.
- Count: how many of these did the agent push back on?

**Scoring:** 0.0 (never pushes back) to 1.0 (always pushes back on questionable requests). Higher is better (but excessive pushback on non-questionable requests is penalized).

---

#### Token Overhead

**Definition:** The ratio of tokens consumed with GRAVITAS vs. without.

```
token_overhead = (tokens_with_GRAVITAS) / (tokens_without_GRAVITAS)
```

**How to measure:**
- Run the same task in both conditions (baseline vs. GRAVITAS).
- Count total tokens consumed (input + output).
- Calculate the ratio.

**Scoring:** 1.0 (no overhead) to ∞ (infinite overhead). Lower is better. Target: <3.0 for v1.

---

#### Task Success Rate

**Definition:** The proportion of tasks completed correctly.

```
task_success_rate = (tasks_completed_correctly) / (total_tasks)
```

**How to determine "completed correctly":**
- Automated: tests pass, build succeeds, requirements met.
- Expert review: does the implementation satisfy the task description?
- Hybrid: automated first, expert for ambiguous cases.

**Scoring:** 0.0 (no tasks correct) to 1.0 (all tasks correct). Higher is better.

---

## 2. How We're Measuring It

### 2.1 Automated Metrics

These metrics can be computed from agent logs without human review:

| Metric | Data Source | Computation |
|--------|------------|-------------|
| Diff scoping ratio | Git diff | `actual_lines / reference_lines` |
| Recon-before-mutation rate | Tool call log | `first_call_is_read / total_tasks` |
| Failure-repetition rate | Tool call log | `repeated_patterns / total_failures` |
| Token overhead | Token counter | `tokens_gravitas / tokens_baseline` |
| Task success rate | Test runner + build | `passing / total` |

### 2.2 Expert Review Metrics

These metrics require human expert review:

| Metric | Data Source | Review Process |
|--------|------------|----------------|
| False-completion rate | Agent output + verification | Expert checks each completion claim against evidence |
| Tier-adherence rate | Agent output + plan | Expert checks each Tier 2+ action for required ceremony |
| Adversarial-catch rate | QA output + implementation | Expert compares QA findings to implementation changes |
| Pushback rate | Agent output + task definitions | Expert identifies questionable requests and checks for pushback |

### 2.3 Human-Rated Metrics

These metrics use blinded human rating:

| Metric | Data Source | Rating Process |
|--------|------------|----------------|
| Outcome-first-ness score | Agent response | 3 blinded raters score 1-5 using rubric |

### 2.4 Data Collection

**What to log for each task run:**

```yaml
task_id: "BF-001"
condition: "gemini+gravitas"
run: 1
start_time: "2026-09-08T10:00:00Z"
end_time: "2026-09-08T10:15:00Z"
tool_calls:
  - tool: "read"
    file: "src/api/handler.ts"
    timestamp: "2026-09-08T10:00:05Z"
  - tool: "grep"
    pattern: "session"
    timestamp: "2026-09-08T10:00:10Z"
  - tool: "edit"
    file: "src/api/handler.ts"
    timestamp: "2026-09-08T10:05:00Z"
  - tool: "bash"
    command: "npm test"
    output: "14/14 passing"
    timestamp: "2026-09-08T10:10:00Z"
completion_claims:
  - claim: "done"
    timestamp: "2026-09-08T10:12:00Z"
    evidence: "npm test — 14/14 passing"
    correct: true
diff:
  files_changed: 1
  lines_added: 8
  lines_removed: 2
plan:
  steps: 4
  adversarial_critique: true
  revision: false
verification:
  tools_run: ["npm test", "npx tsc --noEmit"]
  all_passing: true
qa:
  prompts_run: 5
  issues_found: 1
  issues_fixed: 1
report:
  structure: "outcome-first"
  score: 5
tokens:
  input: 12000
  output: 3000
  total: 15000
```

---

## 3. Scoring Rubrics

### 3.1 Outcome-First-ness Rubric (1-5)

| Score | Description | Example |
|-------|-------------|---------|
| **1** | Process narrative leads. No structured outcome. | "I started by reading the file, then I noticed X, so I changed Y, and then I ran tests..." |
| **2** | Partially outcome-first but buries key info. Outcome mentioned but not structured. | "Fixed the bug. I read the file first and found the issue in the null check. Tests pass." |
| **3** | Outcome-first but lacks specificity or evidence. No file:line references. No command output. | "The bug is fixed. The null check now handles empty strings. Tests are passing." |
| **4** | Outcome-first with specifics and evidence. File:line references. Command output cited. | "Changed `formatDate()` at `src/utils/date.ts:42` — added null guard. `npm test` — 14/14 passing." |
| **5** | Outcome-first with specifics, evidence, uncertainty, and clear writing. | "Changed `formatDate()` at `src/utils/date.ts:42` — added null guard for empty input. `npm test` — 14/14 passing. Cannot verify edge case with timezone conversion — please test locally." |

### 3.2 Plan Quality Rubric (1-5)

| Score | Description |
|-------|-------------|
| **1** | No plan. Agent jumps to execution. |
| **2** | Vague plan. No specific files, steps, or risks. |
| **3** | Structured plan with steps but missing risk analysis or evidence. |
| **4** | Structured plan with steps, risks, and evidence. No adversarial critique. |
| **5** | Full plan with steps, risks, evidence, adversarial critique, and revision. |

### 3.3 Recon Quality Rubric (1-5)

| Score | Description |
|-------|-------------|
| **1** | No recon. Agent edits without reading. |
| **2** | Minimal recon. Reads target file only. No related files. |
| **3** | Reads target + related files. No convention detection. |
| **4** | Reads target + related + config + tests. Detects conventions. |
| **5** | Full recon: module tree, dependencies, git history, conventions, blockers. |

### 3.4 Adversarial-Catch Quality Rubric (1-5)

| Score | Description |
|-------|-------------|
| **1** | No QA performed. |
| **2** | Happy-path QA only. No adversarial testing. |
| **3** | Some adversarial testing (input attacks, boundaries) but incomplete. |
| **4** | Full adversarial testing across all categories (input, boundary, state, security). |
| **5** | Full adversarial testing + catches pre-existing issues + identifies root causes. |

---

## 4. Statistical Methodology

### 4.1 Sample Size

**Per-task sample size:** 3+ runs per task per condition (to account for randomness).

**Total sample size:** 25 tasks × 4 conditions × 3 runs = 300 task runs.

**Justification:** 3 runs per task provides a minimum variance estimate. With 25 tasks, we have sufficient power to detect medium effect sizes (Cohen's d ≥ 0.5) with 80% power at α = 0.05 (based on power analysis for Mann-Whitney U with n=75 per condition).

### 4.2 Significance Testing

**Primary test:** Mann-Whitney U (non-parametric, suitable for ordinal data and small samples).

**When to use:**
- Comparing metrics across conditions (A vs. B, C vs. D).
- Comparing baseline vs. GRAVITAS for the same model.

**When NOT to use:**
- For binary metrics (task success/failure) — use Fisher's exact test instead.
- For comparing more than 2 conditions — use Kruskal-Wallis instead.

**Significance threshold:** α = 0.05 (two-tailed).

### 4.3 Confidence Intervals

**Method:** Bootstrap 95% confidence intervals for all metrics.

**Procedure:**
1. Resample the data with replacement (1000 iterations).
2. Compute the metric for each resample.
3. Take the 2.5th and 97.5th percentiles as the 95% CI.

**Reporting:** Always report point estimate + 95% CI. Example: "False-completion rate: 0.12 [95% CI: 0.05, 0.22]."

### 4.4 Effect Size

**Primary measure:** Cohen's d for continuous metrics, odds ratio for binary metrics.

**Interpretation:**
| Effect Size | Cohen's d | Odds Ratio | Interpretation |
|-------------|-----------|------------|----------------|
| Small | 0.2 | 1.5 | Noticeable but not practically significant |
| Medium | 0.5 | 2.5 | Practically significant |
| Large | 0.8 | 4.0 | Highly practically significant |

**Reporting:** Always report effect size alongside p-value. Statistical significance without practical significance is not enough.

### 4.5 Multiple Comparisons

**Correction:** Bonferroni correction for multiple comparisons within each metric category.

**Procedure:** If comparing K conditions, divide α by K. Example: 4 conditions → α = 0.05/4 = 0.0125.

---

## 5. Controls

### 5.1 Conditions

| Condition | Model | Harness | Skill | Purpose |
|-----------|-------|---------|-------|---------|
| **A: Gemini Baseline** | Gemini 3 Pro | Default | None | Baseline performance without GRAVITAS |
| **B: Gemini + GRAVITAS** | Gemini 3 Pro | Default | GRAVITAS loaded | GRAVITAS effect on Gemini |
| **C: Claude Baseline** | Claude Sonnet/Opus | Claude Code | None | Baseline performance without GRAVITAS |
| **D: Claude + GRAVITAS** | Claude Sonnet/Opus | Claude Code | GRAVITAS loaded | GRAVITAS effect on Claude |

### 5.2 Held Constant

- Same tasks across all conditions.
- Same repositories and commits.
- Same temperature setting (0.0 for determinism where possible).
- Same prompt templates (except for GRAVITAS-loaded conditions).
- Same evaluation criteria and rubrics.

### 5.3 Varied

- Model (Gemini vs. Claude).
- Skill (none vs. GRAVITAS).
- Task type (bug fix, feature, migration, ambiguous, UI, refactor, security).

### 5.4 Blinding

- Human raters do not know which condition produced each response.
- Raters evaluate responses in random order.
- Raters do not see other raters' evaluations until all ratings are complete.

---

## 6. Anti-Gaming Measures

### 6.1 Goodhart's Law Prevention

**Risk:** If the metrics are known, agents may optimize for metrics rather than actual quality.

**Mitigations:**
1. **Secret holdout tasks:** 20% of tasks are not disclosed in advance. Agents cannot pre-optimize for them.
2. **Multi-dimensional metrics:** Optimizing for one metric (e.g., diff size) may hurt another (e.g., task success). The multi-metric profile prevents single-metric gaming.
3. **Expert review:** Automated metrics are supplemented by expert review, which is harder to game.
4. **Adversarial tasks:** Some tasks are designed to诱使 gaming (e.g., a task where the minimal diff is wrong and a larger diff is correct).

### 6.2 Prompt Injection Prevention

**Risk:** Tasks could contain instructions that override the GRAVITAS protocol.

**Mitigations:**
1. **Task sanitization:** All task descriptions are reviewed for injection attempts.
2. **Protocol persistence:** GRAVITAS rules are re-stated at context-length checkpoints.
3. **Adversarial robustness testing:** Explicitly test whether adversarial user input degrades protocol adherence.

### 6.3 Overfitting Prevention

**Risk:** The agent may overfit to the specific tasks in the evaluation suite.

**Mitigations:**
1. **Diverse task suite:** Tasks span 7 categories, multiple languages, multiple complexity levels.
2. **Secret holdout:** 20% of tasks are not disclosed.
3. **Cross-validation:** k-fold cross-validation across task subsets.
4. **Real-world tasks:** Supplement synthetic tasks with real GitHub issues.

---

## 7. Interpretation Framework

### 7.1 Success Criteria

**Primary success criteria (v1):**
1. B closes ≥70% of the gap to C on false-completion rate and diff-scoping ratio.
2. B matches or exceeds C on tasks favoring Gemini's native strengths.
3. B's token overhead is <3× baseline.

**Secondary success criteria (v1):**
1. B improves over A on all metrics (GRAVITAS helps Gemini).
2. D improves over C on all metrics (GRAVITAS helps Claude).
3. No metric regresses by >10% in any condition.

### 7.2 Reporting Standards

**For each metric, report:**
1. Point estimate (mean/median).
2. 95% confidence interval.
3. Effect size (Cohen's d or odds ratio).
4. p-value (from Mann-Whitney U).
5. Sample size.

**Example:**
```
False-completion rate:
- Gemini Baseline: 0.24 [95% CI: 0.14, 0.36]
- Gemini + GRAVITAS: 0.08 [95% CI: 0.02, 0.18]
- Mann-Whitney U: p = 0.003
- Cohen's d: 0.72 (medium-large effect)
- Interpretation: GRAVITAS significantly reduces false-completion rate for Gemini.
```

### 7.3 Visualization

**Bar charts:** Metric comparison across conditions (A, B, C, D).
**Radar charts:** Multi-metric profile per condition.
**Scatter plots:** Token overhead vs. success rate.
**Heatmaps:** Per-task performance across conditions.

### 7.4 Per-Pillar Breakdowns

Do not report only aggregate scores. Report per-pillar breakdowns:
- "GRAVITAS improved Recon quality by 1.2 points (Cohen's d = 0.85)."
- "GRAVITAS improved Diff scoping by 0.3 ratio points (Cohen's d = 0.45)."
- "GRAVITAS had no significant effect on Pushback rate (p = 0.32)."

---

## 8. Limitations

### 8.1 Known Limitations

1. **Synthetic tasks:** Tasks are designed, not real-world. Real-world performance may differ.
2. **Small sample:** 25 tasks per category. May not capture all failure modes.
3. **Single model family:** Only tests Gemini and Claude. Other models may behave differently.
4. **Single harness:** Only tests Antigravity and Claude Code. Other harnesses may interact differently with GRAVITAS.
5. **Temperature 0:** Reduces randomness but may not reflect real-world usage (users typically don't set temperature 0).

### 8.2 Threats to Validity

1. **Internal validity:** Confounding variables (model version, prompt template differences).
2. **External validity:** Results may not generalize to other models, harnesses, or task types.
3. **Construct validity:** Metrics may not fully capture what we intend to measure.
4. **Statistical validity:** Small sample sizes may produce unstable estimates.

---

*This methodology document is part of the GRAVITAS protocol's research foundation. It specifies the evaluation methodology for Phase 4 and ensures reproducibility and rigor in the evaluation.*
