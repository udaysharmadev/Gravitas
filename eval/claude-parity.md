# Comparative Evaluation Framework

> **Status: design only — no Claude or Gemini baseline has been measured for this
> repository.** Gravitas is intended to improve observable engineering behavior;
> it does not impersonate, reproduce, or claim equivalence with another model.

This framework compares a Gravitas-enabled configuration with a pre-registered
control. It may include any model as a control, but every published comparison
must name exact model revisions, prompts, tool environment, task revision,
scoring rubric, raw traces, exclusions, and uncertainty.

## Observable dimensions

| Metric | Observable measurement |
|---|---|
| Recon quality | Target and relevant dependency surface inspected before edit |
| Plan quality | Independently scored file-level plan and named risks |
| Verification evidence | Completion claims linked to recorded validator output |
| Scope control | Changed paths remain within the declared write scope |
| Recovery behavior | Failed action is diagnosed before materially identical retry |
| Outcome-first reporting | Final report identifies result and remaining uncertainty |

Use a published rubric with blinded scoring where feasible. Measure inter-rater
agreement and retain the traces needed to reproduce scores. Avoid subjective
phrases such as “feels like model X” as an outcome variable.

## Procedure

1. Freeze a task registry, repositories, environment, and acceptance criteria.
2. Pre-register control, intervention, allocation, sample size, and exclusions.
3. Run each condition with recorded tool calls and final worktree state.
4. Independently verify task acceptance and score only observable artifacts.
5. Publish failures, ties, variance, and confidence intervals alongside wins.

## Report template

| Dimension | Control | Gravitas | Delta | Uncertainty | Runs |
|---|---:|---:|---:|---:|---:|
| Recon quality | — | — | — | — | — |
| Plan quality | — | — | — | — | — |
| Verification evidence | — | — | — | — | — |
| Scope control | — | — | — | — | — |
| Task success | — | — | — | — | — |

No values belong in this table until the underlying dataset is public or
independently reviewable. See [the production-readiness audit](../docs/production-readiness.md)
for the required release gates.
