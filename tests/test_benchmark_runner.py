import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "benchmarks/runner"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = load("validate", ROOT / "benchmarks/runner/validate.py")
summarize = load("summarize", ROOT / "benchmarks/runner/summarize.py")
run = load("run", ROOT / "benchmarks/runner/run.py")
fixtures = load("fixtures", ROOT / "benchmarks/runner/fixtures.py")
implementation = load("implementation", ROOT / "benchmarks/runner/implementation.py")
compare = load("compare", ROOT / "benchmarks/runner/compare.py")
audit = load("audit", ROOT / "benchmarks/runner/audit.py")


class BenchmarkRunnerTests(unittest.TestCase):
    def test_validator_rejects_false_derived_truth(self):
        schema = json.loads((ROOT / "schemas/episode.schema.json").read_text())
        episode = {
            "task_id": "t", "repo_commit": "abc", "model": "m", "configuration": "c",
            "validator_outputs": [{"criterion": "AC1", "result": "FAIL"}],
            "claimed_success": True, "functional_solve": True, "false_completion": False,
        }
        self.assertIn("functional_solve must be False from validator outputs", validate.episode_errors(episode, schema))

    def test_validator_rejects_aggregate_artifact_cleanly(self):
        self.assertEqual(
            validate.episode_errors([], {}, None),
            ["episode must be a JSON object; aggregate arrays are not episode files"],
        )

    def test_validator_allows_empty_directory_only_when_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, str(ROOT / "benchmarks/runner/validate.py"), "--episodes", directory]
            self.assertNotEqual(subprocess.run(command, check=False).returncode, 0)
            self.assertEqual(subprocess.run([*command, "--allow-empty"], check=False).returncode, 0)

    def test_summary_excludes_invalid_infrastructure_runs(self):
        episodes = [
            {
                "configuration": "c", "functional_solve": True, "claimed_success": True,
                "false_completion": False, "tool_calls": [], "tokens": {"total": 100, "cache_read": 60},
                "validator_outputs": [{"result": "PASS"}, {"result": "PASS"}], "quota_consumed": 2,
                "task_lane": "interrupted-resumed",
                "recovery": {"resumed_from_state": True, "completed_actions_before_resume": 5, "repeated_actions_after_resume": 1},
            },
            {"configuration": "c", "functional_solve": False, "infrastructure_failure": True, "tool_calls": []},
        ]
        result = summarize.summarize(episodes)["c"]
        self.assertEqual(result["fsr"]["rate"], 1.0)
        self.assertEqual(result["median_tokens"], 100)
        self.assertEqual(result["median_cache_read_tokens"], 60)
        self.assertEqual(result["rc"], 1.0)
        self.assertEqual(result["irr"]["rate"], 1.0)
        self.assertEqual(result["ei"]["rate"], 1.0)
        self.assertEqual(result["sqe"], 0.5)

    def test_smoke_episode_is_a_valid_plan_only_pass(self):
        task = {
            "task_id": "PL-001", "commit": "fixture", "title": "Plan", "description": "Investigate.",
            "success_criteria": ["Return a plan"],
        }
        episode = run.build_episode(task, "gemini-3.8-flash", "smoke", "1. Inspect logs\n2. Validate", {"total": 12}, 0.1)
        self.assertTrue(episode["functional_solve"])
        self.assertFalse(validate.episode_errors(episode, {}))

    def test_provider_errors_create_invalid_episode_without_key_material(self):
        task = {
            "task_id": "PL-001", "commit": "fixture", "title": "Plan", "description": "Investigate.",
            "success_criteria": ["Return a plan"],
        }
        episode = run.build_episode(task, "gemini-3.8-flash", "smoke", "", {}, 0.1, "Gemini API returned HTTP 429")
        self.assertTrue(episode["infrastructure_failure"])
        self.assertEqual(episode["validator_outputs"][0]["result"], "INVALID")
        self.assertNotIn("AQ.", json.dumps(episode))

    def test_manifest_registers_thirty_unique_task_specs(self):
        manifest = (ROOT / "benchmarks/manifest.yaml").read_text()
        lanes = re.findall(r"^  L\d+:.*?^    tasks: \[([^]]*)\]", manifest, re.MULTILINE | re.DOTALL)
        task_ids = [task_id.strip() for lane in lanes for task_id in lane.split(",") if task_id.strip()]
        specs = {path.stem for path in (ROOT / "eval/tasks").glob("*.yaml")}
        self.assertEqual(len(lanes), 10)
        self.assertEqual(len(task_ids), 30)
        self.assertEqual(len(set(task_ids)), 30)
        self.assertFalse(set(task_ids) - specs)

    def test_fixture_withholds_acceptance_and_starts_failing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            metadata = fixtures.materialize("BF-001", root)
            # Solver sees only the broken implementation and an import smoke test.
            self.assertFalse((root / "tests" / "test_hidden_acceptance.py").exists())
            self.assertFalse(any("assertEqual" in path.read_text()
                                 for path in (root / "tests").glob("*.py")))
            smoke = subprocess.run(
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=root, capture_output=True, text=True, check=False,
            )
            self.assertEqual(smoke.returncode, 0)
            # The withheld acceptance test fails against the broken fixture.
            hidden = implementation.run_hidden_validation(root, "BF-001")
            self.assertFalse(hidden["passed"])
            self.assertFalse((root / "tests" / "test_hidden_acceptance.py").exists())
            self.assertEqual(metadata["allowed_write_scope"], ["src/target.py"])
            self.assertEqual(len(metadata["hidden_validator_hash"]), 64)

    def test_implementation_runner_denies_scope_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures.materialize("BF-001", root)
            result, violation = implementation.execute_action(
                {"tool": "write", "path": "../outside.py", "content": "bad"}, root, ["src/target.py"]
            )
            self.assertTrue(violation)
            self.assertEqual(result["output"], "SCOPE_VIOLATION")

    def test_implementation_runner_maps_registered_lane_and_rejects_invalid_action(self):
        self.assertEqual(implementation.LANE_BY_TASK["SM-001"], "interrupted-resumed")
        self.assertEqual(implementation.LANE_BY_TASK["LH-001"], "long-horizon")
        with self.assertRaises(ValueError):
            implementation.action_from('{"tool": "delete"}')

    def test_paired_comparison_uses_only_valid_matched_episodes(self):
        episodes = [
            {"task_id": "A", "configuration": "base", "functional_solve": False},
            {"task_id": "A", "configuration": "treated", "functional_solve": True},
            {"task_id": "B", "configuration": "base", "functional_solve": True},
            {"task_id": "B", "configuration": "treated", "functional_solve": True},
            {"task_id": "C", "configuration": "base", "functional_solve": True, "infrastructure_failure": True},
            {"task_id": "C", "configuration": "treated", "functional_solve": True},
        ]
        result = compare.compare(episodes, "base", "treated")
        self.assertEqual(result["paired_episodes"], 2)
        self.assertEqual(result["fsr_delta"], 0.5)
        self.assertEqual(result["mcnemar"]["treatment_only"], 1)
        self.assertFalse(result["publication_ready"])

    def test_release_audit_accepts_current_registry_and_schemas(self):
        self.assertEqual(audit.audit(), [])

    def test_holdout_tasks_rejected_without_flag(self):
        import yaml
        manifest = yaml.safe_load((ROOT / "benchmarks/manifest.yaml").read_text())
        holdout = manifest["holdout"]["tasks"]
        self.assertTrue(len(holdout) >= 3)
        for task_id in holdout:
            error = fixtures.check_holdout(task_id, manifest, False)
            self.assertIsNotNone(error, task_id)
            self.assertIsNone(fixtures.check_holdout(task_id, manifest, True), task_id)
        self.assertIsNone(fixtures.check_holdout("BF-001", manifest, False))

    def test_ablation_configs_isolate_components(self):
        import yaml
        manifest = yaml.safe_load((ROOT / "benchmarks/manifest.yaml").read_text())
        ablations = {c["id"]: c for c in manifest.get("configurations-ablation", [])}
        for expected in ("gravitas-enforcement-flash", "gravitas-context-flash",
                         "gravitas-verification-flash"):
            self.assertIn(expected, ablations, expected)
            self.assertEqual(ablations[expected]["model"], "gemini-3.8-flash")
            self.assertEqual(ablations[expected]["ablation_of"], "gravitas-native-flash")
            self.assertTrue(ablations[expected]["varies"])

    def test_bench_cli_doctor_and_build_corpus(self):
        doctor = subprocess.run(
            [sys.executable, str(ROOT / "benchmarks/cli.py"), "doctor"],
            text=True, capture_output=True, cwd=ROOT, check=False)
        self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
        with tempfile.TemporaryDirectory() as directory:
            build = subprocess.run(
                [sys.executable, str(ROOT / "benchmarks/cli.py"), "build-corpus",
                 "--out", str(Path(directory) / "corpus")],
                text=True, capture_output=True, cwd=ROOT, check=False)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertEqual(json.loads(build.stdout)["built"], 30)

    def test_hidden_test_deterministic_per_task(self):
        self.assertEqual(fixtures.hidden_test_source("BF-001"),
                         fixtures.hidden_test_source("BF-001"))
        self.assertNotEqual(fixtures.hidden_test_source("BF-001"),
                            fixtures.hidden_test_source("BF-002"))
        self.assertEqual(len(fixtures.hidden_test_hash("BF-001")), 64)


if __name__ == "__main__":
    unittest.main()
