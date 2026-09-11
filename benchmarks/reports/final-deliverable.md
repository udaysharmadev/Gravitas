# GRAVITAS Benchmark Project - Final Technical Report

## 1. Current repo problems found
* `benchmarks/benchmark.py` was a legacy v3 text-response scorer and presented itself as the official runner.
* Benchmark Data Model in `schemas/episode.schema.json` conflated model effort with Gravitas effort, and lacked quota/host isolation telemetry.
* Task corpus lacked Stratum A/B distinction and deterministic requirement mapping.
* Environment lacked Antigravity CLI (`agy`), meaning runner could not execute.

## 2. Problems fixed
* Moved `benchmarks/benchmark.py` to `benchmarks/legacy/`.
* Updated `schemas/episode.schema.json` with strict fields for `model`, `model_effort`, `gravitas`, `host`, `execution`, `usage`, `quota`, and `outcome`.
* Created `benchmarks/runner/isolation.py` to handle strict baseline/treatment isolation.
* Defined Stratum A task schema `eval/tasks/STRATUM-A-EXAMPLE.yaml`.
* Verified `skills/gravitas/SKILL.md` is canonically identical to `.agents/`.

## 3. Architecture changes
* `benchmarks/cli.py` introduced as the unified reproducibility entrypoint (`gravitas bench ...`).
* Subprocess execution added to `benchmarks/runner/antigravity.py` to capture headless stream-json from `agy`.
* Metrics pipeline isolated in `benchmarks/runner/metrics.py`.

## 4. Benchmark methodology
* Defined in `benchmarks/protocol-v1.md`, strictly isolating Skill Activation, Behavioral Compliance, and Functional Engineering Performance.

## 5. Exact task corpus status
* Stratum A structure defined. Full 30-task conversion is BLOCKED pending execution capability.

## 6. Exact model configurations discovered from `agy models`
* NOT MEASURED. Environment blocked. `agy` command not found.

## 7. Telemetry captured
* NOT MEASURED. Runner execution blocked.

## 8. Pilot execution status
* NOT MEASURED. Blocked by missing `agy` CLI.

## 9. Production execution status
* NOT MEASURED. Blocked by Pilot.

## 10. Every real numerical result collected
* NOT MEASURED.

## 11. Confidence intervals
* NOT MEASURED.

## 12. Quota findings
* NOT MEASURED.

## 13. Gravitas overhead
* NOT MEASURED.

## 14. Gravitas reliability improvement or regression
* NOT MEASURED.

## 15. Claude-gap comparison
* NOT MEASURED.

## 16. Ablation findings
* NOT MEASURED.

## 17. Known failures
* Runner execution fails entirely due to missing Antigravity CLI in current environment.

## 18. Remaining blockers
* Missing `agy` executable in the environment PATH.
* Authentication and network policies for model access.

## 19. Files changed
* `docs/audits/current-state.md` (New)
* `benchmarks/benchmark.py` -> `benchmarks/legacy/benchmark.py`
* `benchmarks/protocol-v1.md` (New)
* `schemas/episode.schema.json` (Updated)
* `benchmarks/runner/antigravity.py` (New)
* `benchmarks/runner/isolation.py` (New)
* `benchmarks/runner/metrics.py` (New)
* `eval/tasks/STRATUM-A-EXAMPLE.yaml` (New)
* `benchmarks/cli.py` (New)
* `docs/production-readiness.md` (Updated)

## 20. Commands required to reproduce
```bash
./benchmarks/cli.py doctor
./benchmarks/cli.py pilot
./benchmarks/cli.py run --dataset v1 --config baseline-flash --runs 5
./benchmarks/cli.py run --dataset v1 --config gravitas-native-flash --runs 5
./benchmarks/cli.py report --dataset v1
```

## 21. Production-readiness gates G1–G12
See `docs/production-readiness.md`. Current status is largely PARTIAL or BLOCKED due to execution constraints.

## 22. VERDICT
**FAIL** - The architectural shell is in place and methodology strictly defined, but functional benchmarking cannot proceed without the host Antigravity CLI. The system is ready to be executed as soon as the environment provides `agy`.
