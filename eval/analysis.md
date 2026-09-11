# Results Analysis Framework

Framework for analyzing, interpreting, and reporting GRAVITAS evaluation results.

---

## 1. Statistical Tests

### 1.1 Primary Test: Mann-Whitney U

**When to use:** Comparing metrics across two conditions (e.g., A vs. B, C vs. D).

**Why Mann-Whitney:** Non-parametric, suitable for ordinal data and small samples. Does not assume normality.

**Procedure:**
1. For each metric, collect scores from both conditions.
2. Compute Mann-Whitney U statistic.
3. Compute p-value (two-tailed).
4. Apply Bonferroni correction for multiple comparisons.

**Interpretation:**
- p < 0.05: Statistically significant difference.
- p ≥ 0.05: No statistically significant difference.

### 1.2 Bootstrap Confidence Intervals

**When to use:** For all metrics, to quantify uncertainty.

**Procedure:**
1. Resample the data with replacement (1000 iterations).
2. Compute the metric for each resample.
3. Take the 2.5th and 97.5th percentiles as the 95% CI.

**Interpretation:**
- Narrow CI: Precise estimate.
- Wide CI: Uncertain estimate (may need more data).
- CI excluding 0: Significant effect.

### 1.3 Effect Size: Cohen's d

**When to use:** For continuous metrics, to quantify practical significance.

**Formula:**
```
d = (mean1 - mean2) / pooled_std_dev
```

**Interpretation:**
| d | Interpretation |
|---|----------------|
| 0.2 | Small effect |
| 0.5 | Medium effect |
| 0.8 | Large effect |

### 1.4 Multiple Comparisons: Bonferroni Correction

**When to use:** When comparing K conditions or testing K metrics.

**Formula:**
```
adjusted_alpha = alpha / K
```

**Example:** 4 conditions → alpha = 0.05/4 = 0.0125.

---

## 2. Visualization

### 2.1 Bar Charts

**Purpose:** Compare metric values across conditions.

**Structure:**
- X-axis: Conditions (A, B, C, D)
- Y-axis: Metric value
- Error bars: 95% CI
- Color: Condition (blue for baseline, green for GRAVITAS)

**One chart per metric.**

### 2.2 Radar Charts

**Purpose:** Show multi-metric profile per condition.

**Structure:**
- Axes: One per metric (normalized to 0-1 scale)
- Lines: One per condition
- Overlap: Shows how conditions compare across all metrics

**One chart per comparison (A vs. B, C vs. D).**

### 2.3 Scatter Plots

**Purpose:** Show relationship between token overhead and task success.

**Structure:**
- X-axis: Token overhead (log scale)
- Y-axis: Task success rate
- Points: One per task run
- Color: Condition

### 2.4 Heatmaps

**Purpose:** Show per-task performance across conditions.

**Structure:**
- Rows: Tasks (BF-001, FA-001, etc.)
- Columns: Conditions (A, B, C, D)
- Color: Performance (green = good, red = bad)

---

## 3. Success Criteria

### 3.1 Primary Success Criteria (v1)

| Criterion | Metric | Threshold | Status |
|-----------|--------|-----------|--------|
| B closes gap to C on false-completion | False-completion rate | ≥70% gap closed | [ ] |
| B closes gap to C on diff-scoping | Diff scoping ratio | ≥70% gap closed | [ ] |
| B matches C on Gemini-favoring tasks | Task success rate | B ≥ C | [ ] |
| B's token overhead < 3× | Token overhead | < 3.0 | [ ] |

### 3.2 Gap Closure Formula

```
gap_closure = (A_score - B_score) / (A_score - C_score) * 100%
```

Where:
- A_score = Gemini baseline
- B_score = Gemini + GRAVITAS
- C_score = Claude baseline

**Interpretation:** 100% = GRAVITAS closes the entire gap. 70% = closes 70% of the gap.

### 3.3 Secondary Success Criteria

| Criterion | Metric | Threshold | Status |
|-----------|--------|-----------|--------|
| B improves over A | All metrics | B > A | [ ] |
| D improves over C | All metrics | D > C | [ ] |
| No regression > 10% | All metrics | No metric regresses > 10% | [ ] |

---

## 4. Interpretation Guidelines

### 4.1 Statistical vs. Practical Significance

**Always report both:**
- Statistical significance (p-value)
- Practical significance (effect size)

**Example:**
```
False-completion rate:
- Gemini Baseline: 0.24 [95% CI: 0.14, 0.36]
- Gemini + GRAVITAS: 0.08 [95% CI: 0.02, 0.18]
- Mann-Whitney U: p = 0.003 (statistically significant)
- Cohen's d: 0.72 (medium-large effect)
- Interpretation: GRAVITAS significantly reduces false-completion rate for Gemini.
```

### 4.2 Confidence Intervals

**Always report CIs, not just point estimates:**

| CI Width | Interpretation | Action |
|----------|---------------|--------|
| Narrow (< 0.1) | Precise estimate | Report with confidence |
| Medium (0.1-0.2) | Moderate precision | Report with caveat |
| Wide (> 0.2) | Uncertain estimate | Note need for more data |

### 4.3 Per-Pillar Breakdowns

**Do not report only aggregate scores.** Report per-pillar breakdowns:

```
GRAVITAS improved:
- Recon quality by 1.2 points (d = 0.85, large effect)
- Diff scoping by 0.3 ratio points (d = 0.45, medium effect)
- False-completion rate by 0.16 (d = 0.72, medium-large effect)

GRAVITAS had no significant effect on:
- Pushback rate (p = 0.32)
- Failure-repetition rate (p = 0.18)
```

### 4.4 Condition Comparisons

**Report each comparison:**

| Comparison | Key Finding | Effect Size | Interpretation |
|-----------|-------------|-------------|----------------|
| A vs. B | GRAVITAS improves Gemini | d = 0.72 | Medium-large practical significance |
| C vs. D | GRAVITAS improves Claude | d = 0.35 | Small-medium practical significance |
| A vs. C | Claude baseline > Gemini baseline | d = 0.55 | Medium effect |
| B vs. D | GRAVITAS narrows the gap | d = 0.15 | Small effect — gap narrowed |

---

## 5. Report Structure

### 5.1 Executive Summary (1 page)

- Key findings (3-5 bullet points)
- Success criteria status (pass/fail)
- Recommendations (what to optimize, what to keep)

### 5.2 Detailed Results (5-10 pages)

- Per-metric analysis with CIs and effect sizes
- Per-condition profiles
- Per-task breakdowns
- Statistical test results

### 5.3 Visualizations (2-3 pages)

- Bar charts for key metrics
- Radar chart for multi-metric profile
- Heatmap for per-task performance

### 5.4 Recommendations (1-2 pages)

- What to optimize (metrics with room for improvement)
- What to keep (metrics that are already strong)
- What to investigate (unexpected results)
- Phase 5 priorities (based on findings)

---

## 6. Limitations to Acknowledge

### 6.1 Known Limitations

1. **Synthetic tasks:** Results may not generalize to real-world tasks.
2. **Small sample:** 25 tasks per category. May not capture all failure modes.
3. **Single model family:** Only tests Gemini and Claude.
4. **Single harness:** Only tests Antigravity and Claude Code.
5. **Temperature 0:** May not reflect real-world usage.

### 6.2 Threats to Validity

1. **Internal:** Confounding variables (model version, prompt differences).
2. **External:** Results may not generalize to other models/harnesses.
3. **Construct:** Metrics may not fully capture what we intend to measure.
4. **Statistical:** Small samples may produce unstable estimates.

---

*This analysis framework is part of the GRAVITAS evaluation framework. It ensures rigorous, reproducible analysis of evaluation results.*
