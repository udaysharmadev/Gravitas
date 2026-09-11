# GravitasBench

> Status: benchmark infrastructure verified; comparative results pending
> Gravitas v4.0 · Antigravity 2.x · September 2026

GravitasBench is a trajectory-level benchmark for measuring the reliability impact of the Gravitas harness on Gemini models in Antigravity.

## What GravitasBench Measures

GravitasBench does not measure answers. It measures episodes: complete task trajectories including all tool calls, agent decisions, quota consumption, git diffs, and deterministic validator outputs.

**Why trajectory-level?** Harness-Bench (2026) found that trusting agent final messages is insufficient -- you need the full trajectory and final repository state. GravitasBench follows that methodology.

## Metrics

| Metric | Abbreviation | Formula | What it captures |
|--------|:---:|---------|------------------|
| Functional Solve Rate | FSR | solved_tasks / total_tasks | Did the implementation actually work? |
| Requirement Coverage | RC | criteria_with_evidence / total_criteria | Were all stated requirements addressed? |
| Regression Rate | RR | tasks_with_regression / total_tasks | Did the implementation break anything? |
| Scope Violation Rate | SVR | tasks_with_scope_violation / total_tasks | Did the agent touch what it shouldn't? |
| Plan-Only Violation Rate | PVR | unauthorized_writes / plan_only_tasks | Did plan-only mode actually prevent writes? |
| Interruption Recovery Rate | IRR | clean_resumes / interrupted_tasks | Can the agent resume without redoing work? |
| False Completion Rate | FCR | claimed_but_failed / all_claimed | Did the agent claim done when it wasn't? |
| Evidence Integrity | EI | verified_successes / claimed_successes | Are completion claims backed by evidence? |
| Solves per Quota Unit | SQE | successful_tasks / quota_consumed | Efficiency: reliability per quota unit |

## Claude Gap Closure

For each task suite:
```
Gap Closure = (Gravitas Gemini FSR - Baseline Gemini FSR) / (Claude reference FSR - Baseline Gemini FSR) x 100
```

This measures how much of the Gemini-to-Claude reliability gap Gravitas closes on this task suite.

## Configuration Matrix

| Configuration | Model | Gravitas | Status |
|--------------|-------|----------|--------|
| baseline-flash | Gemini 3.8 Flash | None | Pending |
| gravitas-core-flash | Gemini 3.8 Flash | SKILL.md only | Pending |
| gravitas-native-flash | Gemini 3.8 Flash | Full (hooks + skill) | Pending |
| baseline-flash-37 | Gemini 3.7 Flash | None | Pending |
| gravitas-flash-37 | Gemini 3.7 Flash | Full | Pending |
| baseline-pro | Gemini 3.1 Pro | None | Pending |
| gravitas-pro | Gemini 3.1 Pro | Full | Pending |
| reference-sonnet | Sonnet 4.6 | None | Pending |
| reference-opus | Opus 4.6 | None | Pending |

## Task Lanes

| Lane | Description | Tasks | Status |
|------|-------------|:-----:|--------|
| L1 | Isolated bug fix | 3+ | Pending |
| L2 | Multi-file feature | 3+ | Pending |
| L3 | Debugging / root cause | 3+ | Pending |
| L4 | Regression-sensitive refactor | 3+ | Pending |
| L5 | Security-sensitive change | 3+ | Pending |
| L6 | Ambiguous requirements | 3+ | Pending |
| L7 | Plan-only constraint enforcement | 3+ | Pending |
| L8 | Interrupted / resumed task | 3+ | Pending |
| L9 | Tool failure / adversarial | 3+ | Pending |
| L10 | Long-horizon repository task | 3+ | Pending |

Minimum: 30 tasks x 5 runs/config for first credible publication. Target: 100+ tasks.

## Statistical Requirements

All published results must include:
- 95% confidence intervals
- Paired task design across configurations
- McNemar test for paired pass/fail comparisons
- Bootstrap CI for tokens/latency
- Median and p90 for all continuous metrics
- All failures published alongside wins
- Evaluator version and dataset commit pinned
- Infrastructure failures classified INVALID, not FAIL

## How to Reproduce

```bash
# 1. Clone the repository at the published commit
git clone https://github.com/udaysharmadev/Gravitas
git checkout <results-commit>

# 2. Create an isolated environment and install dependencies
python3 -m venv .venv
.venv/bin/python -m pip install -r benchmarks/runner/requirements.txt

# 3. Run one bounded Gemini plan-only smoke episode (uses GEMINI_API_KEY or the
#    local macOS Keychain entry; it grants the model no filesystem or shell tools)
.venv/bin/python benchmarks/runner/run.py --task-file eval/tasks/PL-001.yaml

# 4. Exercise the constrained implementation adapter in a disposable synthetic fixture
.venv/bin/python benchmarks/runner/implementation.py \
  --task-file eval/tasks/BF-001.yaml \
  --output benchmarks/results/gemini-synthetic.json

# 5. Validate results
.venv/bin/python benchmarks/runner/validate.py --episodes benchmarks/results/

# 6. Compare matched configurations only after collecting paired runs
.venv/bin/python benchmarks/runner/compare.py \
  --episodes benchmarks/results/ \
  --baseline baseline-flash \
  --treatment gravitas-native-flash

# 7. Audit schemas, registry cardinality, and trigger-eval data
.venv/bin/python benchmarks/runner/audit.py
```

## Results

Four schema-valid smoke episodes are published in `benchmarks/results/`. They
verify the runner, telemetry shape, derived-truth validation, and CI release
path. They are deliberately **not** comparative model results: they do not form
matched baseline/treatment pairs, do not use eligible implementation fixtures,
and do not measure a Claude-reference gap.

The manifest now registers 30 task specifications. The implementation adapter
materializes a disposable, intentionally failing synthetic fixture for each
registered task. Its model is restricted to reading files, replacing one
allowlisted source file, running one fixed test command, and finishing; every
action and validator result is recorded. The fixture layer proves benchmark
plumbing only. Licensed fixture repositories and hidden deterministic
validators are still required before any implementation episode can be used in
a model comparison. Smoke episodes are ignored by git and must never be
presented as model-comparison results.

When comparative results are published, this section will include:
- N tasks, runs per config
- Antigravity version and Gravitas version
- Date
- 95% CI for all primary metrics
- Link to raw episode data
- Link to reproduce script
