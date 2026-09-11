# Gravitas Production Readiness Gates

| Gate | Description | Status | Evidence Path | Verification Command | Date | Remaining Limitation |
|---|---|---|---|---|---|---|
| G1 | Skill source truth synced | PASS | `docs/audits/current-state.md` | `diff skills/gravitas/SKILL.md .agents/skills/gravitas/SKILL.md` | 2026-09-11 | None |
| G2 | Benchmark Data Model | PASS | `schemas/episode.schema.json` | `cat schemas/episode.schema.json` | 2026-09-11 | Schema created, but no generated runs exist yet. |
| G3 | Runner executes native Antigravity | BLOCKED | None | `agy --version` | 2026-09-11 | `agy` CLI is not available in environment. |
| G4 | Baseline is isolated from Gravitas | PARTIAL | `benchmarks/runner/isolation.py` | Python unit tests (pending) | 2026-09-11 | Code written, waiting for live test. |
| G5 | Deterministic hidden validators | PARTIAL | `eval/tasks/STRATUM-A-EXAMPLE.yaml` | N/A | 2026-09-11 | Examples updated, need full 30 task corpus. |
| G6 | Complete Metrics Pipeline | PARTIAL | `benchmarks/runner/metrics.py` | N/A | 2026-09-11 | Metric definitions exist, execution blocked. |
| G7 | Statistical Analysis Correctness | BLOCKED | None | N/A | 2026-09-11 | Tooling not fully implemented yet. |
| G8 | Reproducibility CLI (`gravitas bench`) | PARTIAL | `benchmarks/cli.py` | `./benchmarks/cli.py doctor` | 2026-09-11 | CLI shell exists, commands blocked. |
| G9 | Pilot Execution (10 tasks x 3 runs) | BLOCKED | None | `./benchmarks/cli.py pilot` | 2026-09-11 | Blocked by missing `agy`. |
| G10 | Primary Benchmark Execution | BLOCKED | None | `./benchmarks/cli.py run` | 2026-09-11 | Blocked by pilot. |
| G11 | Automated Claims Generation | BLOCKED | None | `./benchmarks/cli.py report` | 2026-09-11 | No data to generate claims from. |
| G12 | Final Report Generated | PARTIAL | `benchmarks/reports/final-deliverable.md` | N/A | 2026-09-11 | Generated with "NOT MEASURED" due to blocked execution. |
