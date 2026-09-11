# Human Evaluation Guide

Guide for human raters evaluating GRAVITAS agent responses. Covers evaluation procedure, bias prevention, and calibration.

---

## 1. Evaluation Overview

### 1.1 What You're Rating

You are evaluating agent responses to coding tasks. Your ratings determine whether GRAVITAS improves agent behavior.

### 1.2 What You're NOT Rating

- The implementation quality (focus on the response structure and process).
- The model itself (you don't know which model produced the response).
- The task difficulty (all tasks are treated equally).

### 1.3 Blinding

- You do not know which condition (baseline vs. GRAVITAS) produced each response.
- Responses are anonymized before rating.
- Do not try to guess which condition produced the response.

---

## 2. Metrics You'll Rate

### 2.1 Outcome-First-ness (1-5)

Rate the structure of the agent's response. Does it lead with the outcome or with process narrative?

**Read the rubric:** `rubrics/outcome-first-ness.md`

**Key questions:**
- What is the first thing the user would read?
- Is the outcome stated before the process?
- Are file:line references included?
- Is evidence cited?
- Is uncertainty stated?

### 2.2 Plan Quality (1-5)

Rate the quality of the agent's plan before execution. Did the agent plan appropriately for the task tier?

**Read the rubric:** `rubrics/plan-quality.md`

**Key questions:**
- Is there a structured plan?
- Are specific files and steps identified?
- Is there risk analysis?
- Is there an adversarial critique?
- Was the plan revised based on critique?

### 2.3 Recon Quality (1-5)

Rate the depth of reconnaissance before mutation. Did the agent read enough before editing?

**Read the rubric:** `rubrics/recon-quality.md`

**Key questions:**
- What was the first tool call?
- Which files were read before editing?
- Were tests and config checked?
- Were conventions detected?

### 2.4 Adversarial-Catch Quality (1-5)

Rate the depth of the adversarial self-QA pass. Did the agent try to break its own implementation?

**Read the rubric:** `rubrics/adversarial-catch-quality.md`

**Key questions:**
- Was QA performed?
- Which categories were tested (input, boundary, state, security)?
- Were pre-existing issues caught?
- Were root causes identified?

---

## 3. Rating Procedure

### 3.1 For Each Response

1. **Read the task description** — understand what was asked.
2. **Read the agent's response** — the full output, including plan, implementation, verification, and report.
3. **Read the tool call log** — understand what the agent did (recon, edits, verification).
4. **Rate each metric** — use the rubrics provided.
5. **Note specific strengths and weaknesses** — for calibration.

### 3.2 Rating Order

- Rate all responses for one metric before moving to the next metric.
- This reduces within-metric comparison bias.

### 3.3 Time Per Response

- Estimated: 5-10 minutes per response.
- Do not rush. Accuracy is more important than speed.

---

## 4. Bias Prevention

### 4.1 Common Biases

| Bias | Description | Prevention |
|------|-------------|------------|
| **Anchoring** | First response sets the standard | Rate in random order, not sequentially |
| **Halo effect** | One good metric inflates others | Rate each metric independently |
| **Confirmation bias** | Expecting GRAVITAS to be better | Blind evaluation — don't know which condition |
| **Recency bias** | Recent responses rated differently | Randomize response order |
| **Length bias** | Longer responses rated higher | Focus on structure, not length |

### 4.2 Calibration

- After rating 5 responses, pause and review your ratings.
- Are you using the full 1-5 scale?
- Are your ratings consistent with the rubric?
- Adjust if needed.

### 4.3 Disagreement Resolution

- If you're uncertain, give your best rating and note the uncertainty.
- Do not skip ratings — every response must be rated.
- If two raters disagree by 2+ points, a third rater breaks the tie.

---

## 5. Quality Assurance

### 5.1 Inter-Rater Reliability

- After all ratings are complete, calculate Cohen's kappa.
- If kappa < 0.6, convene a calibration session.
- If kappa < 0.4 after calibration, exclude the metric.

### 5.2 Spot Checks

- 10% of responses are rated by all 3 raters (overlap sample).
- Compare ratings across raters for consistency.
- Discuss discrepancies in calibration sessions.

---

## 6. Rating Forms

### 6.1 Response Rating Form

```
Response ID: [anonymized]
Task ID: [task identifier]

Outcome-First-ness: [1-2-3-4-5]
Notes: [specific strengths/weaknesses]

Plan Quality: [1-2-3-4-5]
Notes: [specific strengths/weaknesses]

Recon Quality: [1-2-3-4-5]
Notes: [specific strengths/weaknesses]

Adversarial-Catch Quality: [1-2-3-4-5]
Notes: [specific strengths/weaknesses]
```

### 6.2 Calibration Form

```
Calibration Session: [date]

Discrepancies discussed:
1. [Response ID] — Metric: [metric] — Rater A: [score] — Rater B: [score]
   Resolution: [agreed score] — Reason: [explanation]

Updated understanding:
- [clarification or adjustment to rubric interpretation]
```

---

## 7. Timeline

| Activity | Duration | Deliverable |
|----------|----------|-------------|
| Rater training | 1 hour | Calibration session |
| Rating phase 1 | 4 hours | First 50 responses rated |
| Calibration check | 30 minutes | Inter-rater reliability check |
| Rating phase 2 | 4 hours | Next 50 responses rated |
| Calibration check | 30 minutes | Inter-rater reliability check |
| Rating phase 3 | 4 hours | Remaining responses rated |
| Final calibration | 1 hour | Final inter-rater reliability |
| **Total** | **~14 hours** | Complete ratings |

---

*This guide is part of the GRAVITAS evaluation framework. It ensures consistent, unbiased human evaluation of agent responses.*
