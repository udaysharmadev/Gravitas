# Performance Measurement Protocol

> **Status: methodology only — no performance results are published.** Earlier
> numerical tables in this file were planning assumptions, not observations from
> a registered experiment. They must not be quoted as Gravitas results.

This protocol measures the cost and possible benefit of using Gravitas against a
pre-registered control condition. It exists so a future release can make useful
claims without turning intuition into marketing.

## Questions

1. What is the change in input/output tokens and wall-clock time per task?
2. Does the intervention change independently scored task success, verification
   quality, scope control, or false-completion rate?
3. Is any observed quality difference worth the added compute and human review?

## Experimental design

For every task, record the exact model/version, provider settings, system prompt,
skill revision, repository revision, environment, random seed where available,
task ID, execution trace, and independent verification result. Use randomized or
counterbalanced assignment, paired tasks where possible, and enough repetitions
to report uncertainty rather than a single percentage.

Do not compare providers using private reasoning traces. Score observable outputs,
tool calls, changed files, validator results, and human rubric judgments.

## Required measures

| Measure | Definition | Report |
|---|---|---|
| Token cost | Input + output tokens recorded by the provider | median, mean, distribution, paired delta |
| Elapsed time | Task receipt to independent verification | median, distribution, paired delta |
| Task success | Independent acceptance-criterion pass | count, rate, confidence interval |
| False completion | Success claim despite failed/missing criterion | count and rate |
| Scope adherence | Changes inside declared scope | count and rate |
| Verification quality | Rubric score from recorded evidence | rubric distribution and agreement |

## Reporting template

| Task family | Control | Gravitas | Delta | Uncertainty | Runs |
|---|---:|---:|---:|---:|---:|
| Bug fix | — | — | — | — | — |
| Feature | — | — | — | — | — |
| Migration | — | — | — | — | — |
| Security review | — | — | — | — | — |

An eventual report must link raw traces, evaluator instructions, task registry
revision, exclusions, failure cases, and the code used to compute every summary.
Absent those artifacts, the correct result is **not measured**.

## Cost-benefit analysis

Keep price and labor assumptions separate from observed outcomes. Publish the
formula, currency date, model pricing source, and sensitivity analysis. A simple
model is:

```text
incremental_cost = provider_cost_delta + reviewer_time_delta × reviewer_rate
net_value = avoided_failure_cost_estimate − incremental_cost
```

The avoided-failure estimate must be labelled as an assumption and varied across
plausible scenarios. Do not infer return on investment from unmeasured error
rates.

## Release bar

Public performance claims require the benchmark acceptance gates in
[production-readiness.md](production-readiness.md), including a reproducible
paired dataset and independent scoring. Until then, Gravitas is a research
preview.
