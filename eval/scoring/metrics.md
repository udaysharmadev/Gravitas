# Metrics Definitions

Operational definitions for all metrics in the GRAVITAS evaluation suite.

---

## Automated Metrics

### Diff Scoping Ratio

**Definition:** Ratio of actual diff size to minimal necessary diff size.

```
diff_scoping_ratio = actual_diff_lines / minimal_necessary_diff_lines
```

**Data source:** Git diff + expert reference solution.

**Scoring:**
| Range | Rating |
|-------|--------|
| 1.0–1.2 | Excellent |
| 1.2–1.5 | Good |
| 1.5–2.0 | Acceptable |
| 2.0–3.0 | Poor |
| >3.0 | Very Poor |

**Pillar:** 4 (Small, Scoped Diffs)

---

### Recon-Before-Mutation Rate

**Definition:** Proportion of non-trivial tasks where the first tool call is read-only.

```
recon_before_mutation_rate = tasks_with_read_only_first_call / total_non_trivial_tasks
```

**Data source:** Tool call log.

**First call is read-only if tool is:** `read`, `glob`, `grep`, `list_dir`, `codebase_search`, `@` reference.

**First call is mutating if tool is:** `write`, `edit`, `bash` (with mutating commands).

**Scoring:** 0.0 (never reads first) to 1.0 (always reads first). Higher is better.

**Pillar:** 1 (Reconnaissance Before Mutation)

---

### Failure-Repetition Rate

**Definition:** Proportion of failed approaches that are re-attempted without modification.

```
failure_repetition_rate = failed_approaches_retried_without_change / total_failed_approaches
```

**Data source:** Tool call log.

**Repetition detected when:** Same tool + same file + similar output (>80% similarity) across consecutive attempts.

**Scoring:** 0.0 (never repeats) to 1.0 (always repeats). Lower is better.

**Pillar:** 8 (Session Memory of Failures)

---

### Token Overhead

**Definition:** Ratio of tokens consumed with GRAVITAS vs. without.

```
token_overhead = tokens_with_GRAVITAS / tokens_without_GRAVITAS
```

**Data source:** Token counter (API response metadata).

**Scoring:** 1.0 (no overhead) to ∞ (infinite overhead). Lower is better.

**Pillar:** Cost metric (not pillar-specific)

---

### Task Success Rate

**Definition:** Proportion of tasks completed correctly.

```
task_success_rate = tasks_completed_correctly / total_tasks
```

**Data source:** Test runner + build output + expert review.

**Determination:**
1. Automated: all tests pass + build succeeds.
2. Expert review: implementation satisfies task description.
3. Hybrid: automated first, expert for ambiguous cases.

**Scoring:** 0.0 (no tasks correct) to 1.0 (all tasks correct). Higher is better.

**Pillar:** Overall metric

---

## Expert Review Metrics

### False-Completion Rate

**Definition:** Proportion of completion claims that are incorrect.

```
false_completion_rate = claims_of_done_that_are_wrong / total_claims_of_done
```

**Data source:** Agent output + verification results.

**How to count claims:**
- Agent says "done," "fixed," "working," "passing," "complete," "implemented," "resolved."
- Any statement asserting task completion.
- Include partial claims: "The first part is done."

**How to determine "wrong":**
- Expert review: does the claim match reality?
- Automated: run verification after the claim — if it fails, the claim was wrong.

**Scoring:** 0.0 (no false completions) to 1.0 (all completions false). Lower is better.

**Pillar:** 5 (Evidence Before Completion Claims)

---

### Tier-Adherence Rate

**Definition:** Proportion of Tier 2+ actions that received the full tier-appropriate ceremony.

```
tier_adherence_rate = tier2_actions_with_full_ceremony / total_tier2_actions
```

**Data source:** Agent output + plan.

**Full ceremony by tier:**
- Tier 2: plan + critique + verification.
- Tier 3: plan + critique + user confirmation + verification.
- Tier 4: plan + critique + confirmation + dry run + rollback plan.

**Scoring:** 0.0 (never follows ceremony) to 1.0 (always follows ceremony). Higher is better.

**Pillar:** 3 (Irreversibility-Scaled Caution)

---

### Adversarial-Catch Rate

**Definition:** Proportion of issues found in QA that were pre-existing (not introduced by the implementation).

```
adversarial_catch_rate = issues_found_in_qa_not_in_implementation / total_qa_findings
```

**Data source:** QA output + implementation changes.

**Scoring:** 0.0 (no catches) to 1.0 (all findings are catches). Higher indicates stronger adversarial depth.

**Pillar:** 6 (Adversarial Self-QA)

---

### Pushback Rate

**Definition:** Proportion of questionable requests where the agent pushed back appropriately.

```
pushback_rate = appropriate_pushbacks / total_questionable_requests
```

**Data source:** Agent output + task definitions.

**Questionable requests identified by:** Expert review of task definitions (tasks that skip tests, bad architecture, security risks, scope creep).

**Scoring:** 0.0 (never pushes back) to 1.0 (always pushes back). Higher is better (but excessive pushback on non-questionable requests is penalized).

**Pillar:** 10 (Calibrated Pushback)

---

## Human-Rated Metrics

### Outcome-First-ness Score

**Definition:** Human-rated quality of response structure on a 1-5 scale.

**Data source:** Agent response text.

**Rubric:**
| Score | Description |
|-------|-------------|
| 1 | Process narrative leads. No structured outcome. |
| 2 | Partially outcome-first but buries key information. |
| 3 | Outcome-first but lacks specificity or evidence. |
| 4 | Outcome-first with specifics and evidence. |
| 5 | Outcome-first with specifics, evidence, uncertainty, and clear writing. |

**Rating process:**
- 3 independent blinded raters per response.
- Average the 3 ratings.
- Calculate inter-rater reliability (Cohen's kappa).

**Pillar:** 7 (Outcome-First Reporting)

---

## Pillar-to-Metric Summary

| Pillar | Metric | Type | Direction |
|--------|--------|------|-----------|
| 1: Recon | Recon-before-mutation rate | Automated | Higher = better |
| 2: Plan | Plan quality score | Human-rated | Higher = better |
| 3: Tiering | Tier-adherence rate | Expert review | Higher = better |
| 4: Diff Scoping | Diff scoping ratio | Automated | Lower = better |
| 5: Evidence | False-completion rate | Expert review | Lower = better |
| 6: Self-QA | Adversarial-catch rate | Expert review | Higher = better |
| 7: Reporting | Outcome-first-ness score | Human-rated | Higher = better |
| 8: Memory | Failure-repetition rate | Automated | Lower = better |
| 9: Native Strengths | (No dedicated metric) | — | — |
| 10: Pushback | Pushback rate | Expert review | Higher = better |
| Cost | Token overhead | Automated | Lower = better |
| Overall | Task success rate | Automated + expert | Higher = better |

---

*This document is part of the GRAVITAS evaluation framework. It defines the operational metrics for Phase 4.*
