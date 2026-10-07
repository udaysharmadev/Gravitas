# Superseded benchmark scripts

Quarantined on 2026-09-15. These files are kept for provenance only; none is
wired into CI, tests, or documented workflows. Do not run them for new
evidence.

| File | Superseded by | Reason |
|------|---------------|--------|
| `repair_runner.py` | `benchmarks/runner/agy_runner.py`, root `repair_runner_v4.py` | v1 canary runner; its `setup_global_config` destructively deleted `~/.gemini/config` (that is why `run.sh` wrapped it) |
| `repair_runner_v2.py` | `repair_runner_v4.py` | untracked intermediate; introduced manifest-based contamination checks now living in the v4 chain |
| `repair_runner_v3.py` | `repair_runner_v4.py` | broken at HEAD: read `fixtures/L1_simple_bug/manifest.yaml`, which never existed |
| `report_repair.py` | `report_v3.py` | reports on v1 canary output only |
| `report_v2.py` | `report_v3.py` | crashes at HEAD: re-derives git diffs inside deleted `/tmp/gravitasbench` workspaces |
| `run_smoke.py` | smoke gate embedded in `repair_runner_v4.py` | evidence-counting loop was dead code (`pass`), returned True unconditionally |
| `framework.py` | smoke gate embedded in `repair_runner_v4.py` | duplicated smoke/isolation logic; PreToolUse counter never incremented |
| `pilot_runner.py` | `benchmarks/runner/agy_runner.py` | engine of the pilot era invalidated as `INVALID_METHODOLOGY` (`benchmarks/legacy/README.md`) |
| `create_pilot_fixtures.py` | `create_repaired_canary.py`, `benchmarks/corpus/build_corpus.py` | generated the same `add(a,b)` fixture for lanes L2–L10 (fake lane diversity) |
| `test_appdata_dir.py` | nothing (diagnostic) | probe with no assertions; superseded by canary contamination checks |
| `test_root_plugin.py` | nothing | crashed at HEAD: copied root `plugin.json`/`hooks.json`, deleted in commit `33143e5` |
| `test_reporter.py` | `tests/` suite | passed, but tested only `repair_runner_v2.check_contamination` |
| `run.sh` | `benchmarks/cli.py` | wrapper around v1's destructive config wipe |
| `benchmark.py` | `benchmarks/runner/*` | heuristic keyword scorer; its engine was an acknowledged stub and its corpus was empty |
