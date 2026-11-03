# Benchmark Methodology

GravitasBench measures episodes (full trajectories + final repo state),
never final messages. Full protocol: `benchmarks/README.md`.

## What is measured

FSR, requirement coverage, regression/scope-violation rates, plan-only
violation rate, interruption recovery, false completion, evidence
integrity, solves-per-quota — rates with Wilson 95% confidence intervals;
tokens/latency as median + p90; paired McNemar tests and bootstrap solve-rate
deltas. Infrastructure failures are classified INVALID and excluded from
model-outcome denominators, but remain visible in reports.

## Outcome integrity

Every recorded validator is mandatory. A failed simulated checkpoint,
scope check, step budget, or additional regression validator prevents a
functional solve even when hidden tests pass. `outcome.tests_passing`
means hidden acceptance passed; `outcome.validators_passing` separately
records whether **all** validator results passed.

The report pipeline rejects contradictory derived fields, malformed
outcome components, and duplicate validator criteria before aggregation.
Known implementation components are checked against their individual
validator results, not just against the final conjunction. A disclosed
`simulated_approval` requires its checkpoint result; simulated approval is
never human approval.

## Honesty gates (enforced in code)

A comparison is structurally publication-ready only when all of these hold:

- At least **30 distinct tasks**, with at least **5 valid paired runs per
  task**. Thirty repeats of one task do not satisfy this requirement.
- Each episode explicitly declares `evidence_kind: repository`. The
  built-in runners emit `smoke` or `synthetic`, which are never eligible.
  Missing evidence kind or provenance remains preview-only.
- Episode identities `(task_id, run_index, configuration)` are unique;
  `run_index` is a positive integer. Duplicate identities are rejected,
  not silently overwritten.
- Every valid episode has a baseline/treatment partner. A pair containing
  an INVALID episode is excluded from paired estimates; infrastructure
  failures must still be reported.
- Pair members use the same model, effort, repository commit, fixture,
  prompt, hidden validator, dataset revision, host revision, and evaluator
  revision. Cross-model references are exploratory and cannot pass this
  within-model publication gate.
- Repeated runs of a task use the same task artifacts. Each configuration
  uses a consistent model, effort, host, dataset, harness, configuration,
  and evaluator revision across the experiment.
- All selected episodes, including INVALID runs, pass outcome validation
  and declare the provenance fields below. Excluding an infrastructure
  failure from performance denominators does not exempt its evidence from
  validation.
- Every configuration included in a published report is covered by an
  eligible comparison; an unrelated smoke configuration cannot inherit
  another pair's readiness. Report writing rechecks supplied episodes and
  recomputes comparisons rather than trusting a caller's readiness flag.

`compare()` returns `publication_blockers`, `paired_tasks`, and
`min_pairs_per_task`. Preview reports retain the research-preview banner
and explain blockers. `--publish` fails before creating report artifacts
when eligibility is missing. Passing this gate is **not** a claim of
statistical significance, model superiority, or independently authenticated
provenance.

### Repository provenance declarations

The runner episode format accepts these additive fields. Existing preview
episodes need not be rewritten merely to remain readable.

| Location | Required for publication |
|---|---|
| Episode | `evidence_kind`, `run_index`, `model`, `effort`, `repo_commit`, `hidden_validator_hash` |
| `provenance` | `repository_url`, `repository_license`, `dataset_version`, `fixture_hash`, `prompt_hash`, `model_revision`, `host_revision`, `harness_revision`, `configuration_hash`, `evaluator_revision` |

`repo_commit`, `dataset_version`, `harness_revision`, and
`evaluator_revision` are full Git hashes (40 or 64 hex characters).
Fixture, prompt, hidden-validator, and configuration hashes are SHA-256
digests. Model and host revisions must be explicit, nonempty identifiers,
not moving placeholders such as `latest` or `HEAD`. Configuration hashes
and harness revisions may differ between baseline and treatment, but must
remain consistent within each configuration.

These fields are **declarations**. Format and pair-consistency checks do
not prove that a repository was checked out, a license permits reuse, a
hash matches a retained artifact, or a model identifier is immutable.
Release review still requires the actual licensed fixture, executable
hidden validator, archived trajectories, configuration artifacts, and a
reproduction procedure. The independent source/validator custody and
artifact authentication needed for that review are not implemented by
this metadata gate.

### Other boundaries

- Solver worktrees do not contain hidden acceptance tests during the
  trajectory; those tests are materialized only after it ends. Episodes
  record the hidden-validator hash; exported reports redact validator
  output. This is not an operating-system sandbox guarantee.
- Holdout tasks (L10) are refused in dev runs without `--include-holdout`.
- Every public performance number needs a versioned raw artifact and a
  reproducible experiment, not just a passing report flag.
- Repeated runs are correlated within tasks. The current episode-level
  bootstrap/McNemar outputs are exploratory; a release study must specify
  its sampling unit and account for task clustering before inference.

## Current status

The registry contains **48 task specifications across 10 lanes**:
30 core + 5 negative + 5 trap + 8 harvested. The executable fixture factory
still rotates only five synthetic exercises. HARV metadata does not make
the implementation runner execute the pinned source repository.

No release-grade repository execution pipeline, multi-family paired
experiment, or published comparison is established. Current runners remain
plumbing-only and publication-ineligible. See
[the project review](project-review-2026-11-03.md) and
[the production-readiness board](production-readiness.md).
