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

    def test_fixture_is_disposable_and_starts_with_a_failing_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            metadata = fixtures.materialize("BF-001", root)
            result = subprocess.run(
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=root, capture_output=True, text=True, check=False,
            )
            self.assertFalse(result.returncode == 0)
            self.assertEqual(metadata["allowed_write_scope"], ["src/target.py"])

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


if __name__ == "__main__":
    unittest.main()
