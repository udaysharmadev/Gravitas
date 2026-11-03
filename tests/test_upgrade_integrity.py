"""Regression coverage for runtime and benchmark evidence integrity."""
import copy
import io
import json
import runpy
import shlex
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "gravitas-antigravity" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import test_benchmark_runner as bench
import test_runtime
from gravitas_evidence import criterion_states
import stop_gate


UNIT = ["python", "-m", "unittest"]
LINT = ["python", "lint.py"]


def runtime_contract():
    return {
        "acceptance_criteria": [{
            "id": "AC1", "statement": "checks pass", "validators": ["unit", "lint"],
        }],
        "validators": [
            {"id": "unit", "command": UNIT, "criterion_ids": ["AC1"]},
            {"id": "lint", "command": LINT, "criterion_ids": ["AC1"]},
        ],
        "required_validators": ["unit", "lint"],
    }


def owned(validator_id, verdict, second, criteria=None, command=None):
    return {
        "source": "validator", "validator_id": validator_id,
        "criterion_ids": ["AC1"] if criteria is None else criteria,
        "command": command or (UNIT if validator_id == "unit" else LINT),
        "verdict": verdict, "exit_code": 0 if verdict == "PASS" else 1,
        "event_hash": f"event-{second}",
        "timestamp": f"2026-11-03T10:00:{second:02d}+00:00",
    }


class LatestValidatorTests(unittest.TestCase):
    def test_later_lint_pass_cannot_mask_unit_failure(self):
        evidence = [owned("unit", "PASS", 1), owned("lint", "PASS", 2),
                    owned("unit", "FAIL", 3), owned("lint", "PASS", 4)]
        states = criterion_states(runtime_contract(), evidence)
        self.assertEqual(states["AC1"]["status"], "FAIL")
        self.assertFalse(states["AC1"]["fresh"])
        evidence.append(owned("unit", "PASS", 5))
        self.assertEqual(criterion_states(runtime_contract(), evidence)["AC1"]["status"], "PASS")

    def test_all_assigned_validators_must_cover_the_criterion(self):
        states = criterion_states(runtime_contract(), [owned("unit", "PASS", 1)])
        self.assertEqual(states["AC1"]["status"], "PENDING")

    def test_validator_side_assignments_require_all_assigned_checks(self):
        contract = runtime_contract()
        contract["acceptance_criteria"][0].pop("validators")
        states = criterion_states(contract, [owned("unit", "PASS", 1)])
        self.assertEqual(states["AC1"]["status"], "PENDING")

    def test_unlinked_failure_invalidates_earlier_bound_pass(self):
        evidence = [owned("unit", "PASS", 1), owned("lint", "PASS", 2),
                    owned("unit", "FAIL", 3, criteria=[])]
        self.assertEqual(criterion_states(runtime_contract(), evidence)["AC1"]["status"], "FAIL")

    def test_command_must_match_current_declaration(self):
        evidence = [owned("unit", "PASS", 1),
                    owned("lint", "PASS", 2, command=["echo", "not-lint"])]
        self.assertNotEqual(criterion_states(runtime_contract(), evidence)["AC1"]["status"], "PASS")

    def test_separately_bound_passes_for_same_validator_remain_usable(self):
        contract = {
            "acceptance_criteria": [{"id": "AC1", "statement": "first", "validators": ["unit"]},
                                    {"id": "AC2", "statement": "second", "validators": ["unit"]}],
            "validators": [{"id": "unit", "command": UNIT, "criterion_ids": ["AC1", "AC2"]}],
        }
        states = criterion_states(contract, [owned("unit", "PASS", 1),
                                             owned("unit", "PASS", 2, criteria=["AC2"])])
        self.assertEqual([info["status"] for info in states.values()], ["PASS", "PASS"])

    def test_failed_validator_must_recover_each_criterion_binding(self):
        contract = {
            "acceptance_criteria": [{"id": "AC1", "statement": "first", "validators": ["unit"]},
                                    {"id": "AC2", "statement": "second", "validators": ["unit"]}],
            "validators": [{"id": "unit", "command": UNIT, "criterion_ids": ["AC1", "AC2"]}],
        }
        evidence = [owned("unit", "PASS", 1, criteria=["AC1", "AC2"]),
                    owned("unit", "FAIL", 2, criteria=[]),
                    owned("unit", "PASS", 3, criteria=["AC2"])]
        states = criterion_states(contract, evidence)
        self.assertEqual(states["AC1"]["status"], "PENDING")
        self.assertEqual(states["AC2"]["status"], "PASS")

    def test_latest_failure_with_equal_timestamp_still_wins(self):
        evidence = [owned("unit", "PASS", 1), owned("lint", "PASS", 1),
                    owned("unit", "FAIL", 1)]
        self.assertEqual(criterion_states(runtime_contract(), evidence)["AC1"]["status"], "FAIL")

    def test_write_requires_fresh_results_from_every_assigned_validator(self):
        evidence = [owned("unit", "PASS", 1), owned("lint", "PASS", 2),
                    {"source": "write", "timestamp": "2026-11-03T10:00:03+00:00"},
                    owned("lint", "PASS", 4)]
        self.assertEqual(criterion_states(runtime_contract(), evidence)["AC1"]["status"], "PENDING")

    def test_latest_malformed_execution_cannot_revive_an_older_pass(self):
        evidence = [owned("unit", "PASS", 1), owned("lint", "PASS", 2),
                    {**owned("unit", "PASS", 3), "timestamp": "invalid"}]
        self.assertNotEqual(criterion_states(runtime_contract(), evidence)["AC1"]["status"], "PASS")

    def test_legacy_unassigned_criteria_still_accept_owned_evidence(self):
        contract = {"acceptance_criteria": [{"id": "AC1", "statement": "legacy"}]}
        self.assertEqual(criterion_states(contract, [owned("unit", "PASS", 1)])["AC1"]["status"], "PASS")

    def test_legacy_command_requirement_checks_latest_execution(self):
        contract = {"acceptance_criteria": [{"id": "AC1", "statement": "first"}],
                    "required_validators": [shlex.join(LINT)]}
        evidence = [owned("unit", "PASS", 1), owned("lint", "PASS", 2, criteria=[]),
                    owned("lint", "FAIL", 3, criteria=[])]
        output = io.StringIO()
        with patch.object(stop_gate, "session_dir_for_payload", return_value=Path("session")), \
             patch.object(stop_gate, "load_contract", return_value=contract), \
             patch.object(stop_gate, "load_evidence", return_value=evidence), \
             patch.object(stop_gate, "load_state", return_value={}), \
             patch.object(stop_gate, "load_failures", return_value=[]), \
             patch.object(stop_gate, "incomplete_children", return_value=[]), \
             patch.object(stop_gate, "verify_with_anchor", return_value=(True, "verified")), \
             patch.object(stop_gate, "count_stop_gate_cycles", return_value=0), \
             patch.object(stop_gate, "record_stop_gate_cycle"), \
             patch("sys.stdin", io.StringIO("{}")), redirect_stdout(output):
            stop_gate.main()
        self.assertEqual(json.loads(output.getvalue())["decision"], "continue")


class CompletionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.unit = [sys.executable, "-c",
                     "from pathlib import Path; raise SystemExit(int(Path('broken').exists()))"]
        self.lint = [sys.executable, "-c", "pass"]

    def init(self, both_assigned=True):
        contract = {
            "mode": "implement", "objective": "latest evidence governs completion",
            "acceptance_criteria": [{"id": "AC1", "statement": "checks pass",
                                     "validators": ["unit", "lint"] if both_assigned else ["lint"]}],
            "validators": [{"id": "unit", "command": self.unit,
                            "criterion_ids": ["AC1"] if both_assigned else []},
                           {"id": "lint", "command": self.lint, "criterion_ids": ["AC1"]}],
        }
        result = test_runtime.run_script("init_session.py", None, "--task-id", "latest",
                                         "--contract-json", json.dumps(contract), cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.root / ".gravitas" / "sessions" / "latest"

    def run_validator(self, session, identifier, bind=True, expected=0):
        args = ["--session-dir", str(session), "--validator-id", identifier]
        if bind:
            args += ["--criterion-id", "AC1"]
        command = self.unit if identifier == "unit" else self.lint
        result = test_runtime.run_script("validator_runner.py", None, *args, "--", *command,
                                         cwd=self.root)
        self.assertEqual(result.returncode, expected, result.stderr)

    def test_latest_failure_blocks_stop_and_recovery_until_repaired(self):
        session = self.init()
        self.run_validator(session, "unit")
        self.run_validator(session, "lint")
        (self.root / "broken").write_text("broken")
        self.run_validator(session, "unit", expected=1)
        self.run_validator(session, "lint")
        gate = json.loads(test_runtime.run_script("stop_gate.py", {}, cwd=self.root).stdout)
        self.assertEqual(gate["decision"], "continue")
        self.assertIn("unit", gate["reason"])
        result = test_runtime.run_script("post_invocation.py", {}, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((session / "state.json").read_text())
        self.assertEqual(state["completed_criteria"], [])
        self.assertEqual(state["pending_criteria"], ["AC1"])
        self.assertEqual(json.loads((session / "coverage.json").read_text()), {"AC1": "FAIL"})
        (self.root / "broken").unlink()
        self.run_validator(session, "unit")
        gate = json.loads(test_runtime.run_script("stop_gate.py", {}, cwd=self.root).stdout)
        self.assertEqual(gate, {"decision": "allow"})

    def test_required_unbound_validator_failure_blocks_stop(self):
        session = self.init(both_assigned=False)
        self.run_validator(session, "unit", bind=False)
        self.run_validator(session, "lint")
        (self.root / "broken").write_text("broken")
        self.run_validator(session, "unit", bind=False, expected=1)
        gate = json.loads(test_runtime.run_script("stop_gate.py", {}, cwd=self.root).stdout)
        self.assertEqual(gate["decision"], "continue")
        self.assertIn("unit", gate["reason"])

    def test_recovery_does_not_keep_failed_criterion_completed(self):
        session = self.init()
        self.run_validator(session, "unit")
        self.run_validator(session, "lint")
        test_runtime.run_script("post_invocation.py", {}, cwd=self.root)
        (self.root / "broken").write_text("broken")
        self.run_validator(session, "unit", expected=1)
        result = test_runtime.run_script("post_invocation.py", {}, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((session / "state.json").read_text())
        self.assertEqual(state["completed_criteria"], [])
        self.assertEqual(state["pending_criteria"], ["AC1"])
        self.assertEqual(json.loads((session / "coverage.json").read_text()), {"AC1": "FAIL"})


def implementation_episode(tier=1, summary="fixed"):
    task = {"task_id": "BF-001", "commit": "fixture", "description": "Fix.", "tier": tier}
    action = json.dumps({"tool": "finish", "summary": summary})
    with patch.object(bench.implementation, "api_key", return_value="unused-mocked-key"), \
         patch.object(bench.implementation, "generate_content", return_value=(action, {})), \
         patch.object(bench.implementation, "run_hidden_validation",
                      return_value={"passed": True, "output": "hidden ok"}):
        return bench.implementation.run_episode(task, "model", "configuration", max_steps=1)


class BenchmarkOutcomeIntegrityTests(unittest.TestCase):
    def test_denied_checkpoint_round_trips_as_unsolved(self):
        episode = implementation_episode(tier=2, summary="drop table users")
        self.assertFalse(episode["functional_solve"])
        self.assertTrue(episode["false_completion"])
        self.assertTrue(episode["outcome"]["tests_passing"])
        self.assertFalse(episode["outcome"]["validators_passing"])
        self.assertEqual(bench.validate.episode_errors(episode, {}), [])

    def test_checkpoint_failure_cannot_be_rewritten_as_a_solve(self):
        episode = implementation_episode(tier=2, summary="drop table users")
        episode.update(functional_solve=True, false_completion=False)
        episode["outcome"].update(tests_passing=True, functional_solve=True, validators_passing=True)
        errors = bench.validate.episode_errors(episode, {})
        self.assertIn("functional_solve must be False from validator outputs", errors)

    def test_additional_mandatory_validator_failure_blocks_solve(self):
        episode = implementation_episode()
        episode["validator_outputs"].append({"criterion": "No regression", "result": "FAIL"})
        errors = bench.validate.episode_errors(episode, {})
        self.assertIn("functional_solve must be False from validator outputs", errors)

    def test_duplicate_validator_criteria_are_rejected(self):
        episode = implementation_episode()
        episode["validator_outputs"].insert(0, {"criterion": "Hidden acceptance", "result": "FAIL"})
        errors = bench.validate.episode_errors(episode, {})
        self.assertTrue(any("duplicate" in error for error in errors), errors)
        self.assertIn("functional_solve must be False from validator outputs", errors)

    def test_invalid_result_cannot_be_overwritten_by_duplicate_pass(self):
        episode = implementation_episode()
        episode["validator_outputs"].insert(0, {"criterion": "Hidden acceptance", "result": "INVALID"})
        self.assertIn("infrastructure_failure must be True from validator outputs",
                      bench.validate.episode_errors(episode, {}))

    def test_nonstring_criterion_is_rejected_without_crashing(self):
        episode = implementation_episode()
        episode["validator_outputs"].append({"criterion": ["invalid"], "result": "PASS"})
        errors = bench.validate.episode_errors(episode, {})
        self.assertTrue(any("criterion" in error for error in errors), errors)

    def test_each_outcome_component_must_match_its_evidence(self):
        episode = implementation_episode()
        episode["validator_outputs"][2]["result"] = "FAIL"
        episode.update(functional_solve=False, false_completion=True)
        episode["outcome"].update(tests_passing=False, finished_normally=True,
                                   validators_passing=False, functional_solve=False)
        errors = bench.validate.episode_errors(episode, {})
        self.assertTrue(any("tests_passing" in error for error in errors), errors)
        self.assertTrue(any("finished_normally" in error for error in errors), errors)

    def test_malformed_outcome_components_do_not_skip_validation(self):
        for value in ("true", None, 1):
            with self.subTest(value=value):
                episode = implementation_episode()
                episode["outcome"]["tests_passing"] = value
                errors = bench.validate.episode_errors(episode, {})
                self.assertTrue(any("tests_passing" in error for error in errors), errors)

    def test_simulated_checkpoint_cannot_be_removed_from_episode(self):
        episode = implementation_episode(tier=2)
        episode["validator_outputs"] = [item for item in episode["validator_outputs"]
                                          if item["criterion"] != "Tier-2 checkpoint (simulated)"]
        errors = bench.validate.episode_errors(episode, {})
        self.assertTrue(any("checkpoint" in error for error in errors), errors)

    def test_smoke_episode_remains_valid_but_explicitly_smoke(self):
        episode = bench.run.build_episode({"task_id": "PL-001", "commit": "fixture"},
                                          "model", "smoke", "1. Inspect", {}, 0.1)
        self.assertEqual(episode["evidence_kind"], "smoke")
        self.assertEqual(bench.validate.episode_errors(episode, {}), [])

    def test_failed_smoke_cannot_falsify_individual_components(self):
        episode = bench.run.build_episode({"task_id": "PL-001", "commit": "fixture"},
                                          "model", "smoke", "no numbered plan", {}, 0.1)
        episode["outcome"]["tests_passing"] = True
        errors = bench.validate.episode_errors(episode, {})
        self.assertTrue(any("tests_passing" in error for error in errors), errors)

    def test_generic_legacy_outcome_still_checks_original_components(self):
        episode = {
            "task_id": "legacy", "configuration": "c", "claimed_success": False,
            "functional_solve": False, "false_completion": False, "infrastructure_failure": False,
            "validator_outputs": [{"criterion": "legacy acceptance", "result": "FAIL"}],
            "outcome": {"tests_passing": True, "finished_normally": True, "scope_ok": True,
                        "infrastructure_failure": False, "functional_solve": False},
        }
        self.assertIn("outcome components disagree with validator outputs",
                      bench.validate.episode_errors(episode, {}))

    def test_infrastructure_smoke_round_trips_without_a_model_call(self):
        episode = bench.run.build_episode({"task_id": "PL-001", "commit": "fixture"},
                                          "model", "smoke", "", {}, 0.1, error="provider timeout")
        self.assertEqual(bench.validate.episode_errors(episode, {}), [])

    def test_implementation_episode_is_explicitly_synthetic(self):
        self.assertEqual(implementation_episode()["evidence_kind"], "synthetic")


def repository_episodes(tasks=30, runs=5):
    episodes = []
    for task_index in range(tasks):
        for run_index in range(1, runs + 1):
            for configuration in ("base", "treated"):
                episodes.append({
                    "task_id": f"TASK-{task_index:03d}", "run_index": run_index,
                    "configuration": configuration, "model": "test-model", "effort": "eco",
                    "repo_commit": "a" * 40, "hidden_validator_hash": "b" * 64,
                    "evidence_kind": "repository",
                    "provenance": {
                        "repository_url": "https://example.org/test/repository",
                        "repository_license": "MIT", "dataset_version": "c" * 40,
                        "fixture_hash": "d" * 64, "prompt_hash": "e" * 64,
                        "model_revision": "test-model-2026-11-03", "host_revision": "test-host-1.0",
                        "harness_revision": "f" * 40, "configuration_hash": "1" * 64,
                        "evaluator_revision": "2" * 40,
                    },
                    "validator_outputs": [{"criterion": "Acceptance", "result": "PASS"}],
                    "claimed_success": True, "functional_solve": True,
                    "false_completion": False, "infrastructure_failure": False,
                })
    return episodes


class PublicationIntegrityTests(unittest.TestCase):
    def compare(self, episodes):
        with patch.object(bench.compare, "bootstrap_delta", return_value=[0.0, 0.0]):
            return bench.compare.compare(episodes, "base", "treated")

    def test_thirty_repeated_smoke_pairs_never_become_publishable(self):
        episodes = []
        for index in range(1, 31):
            for configuration in ("base", "treated"):
                episode = bench.run.build_episode({"task_id": "PL-001", "commit": "fixture"},
                                                  "model", configuration, "1. Inspect", {}, 0.1)
                episode["run_index"] = index
                episodes.append(episode)
        comparison = self.compare(episodes)
        self.assertFalse(comparison["publication_ready"])
        with self.assertRaisesRegex(ValueError, "publication gate"):
            bench.report.render_markdown({}, [comparison], publish=True)

    def test_synthetic_marker_blocks_even_with_full_declared_metadata(self):
        episodes = repository_episodes()
        for episode in episodes:
            episode["evidence_kind"] = "synthetic"
        comparison = self.compare(episodes)
        self.assertFalse(comparison["publication_ready"])
        self.assertTrue(any("synthetic" in reason for reason in comparison["publication_blockers"]))

    def test_missing_provenance_is_preview_only(self):
        episodes = repository_episodes()
        episodes[0].pop("provenance")
        self.assertFalse(self.compare(episodes)["publication_ready"])

    def test_missing_evidence_kind_is_preview_only(self):
        episodes = repository_episodes()
        episodes[0].pop("evidence_kind")
        self.assertFalse(self.compare(episodes)["publication_ready"])

    def test_thirty_pairs_are_not_thirty_tasks_times_five_runs(self):
        for tasks, runs in ((30, 1), (1, 150), (29, 6), (30, 4)):
            with self.subTest(tasks=tasks, runs=runs):
                self.assertFalse(self.compare(repository_episodes(tasks, runs))["publication_ready"])

    def test_balanced_declared_repository_design_can_clear_structural_gate(self):
        comparison = self.compare(repository_episodes())
        self.assertTrue(comparison["publication_ready"])
        self.assertEqual(comparison["paired_tasks"], 30)
        self.assertEqual(comparison["min_pairs_per_task"], 5)
        self.assertEqual(comparison["publication_blockers"], [])
        self.assertTrue(bench.report.publication_ready([comparison]))

    def test_valid_failed_repository_runs_remain_eligible_evidence(self):
        episodes = repository_episodes()
        for episode in episodes:
            if episode["configuration"] == "treated":
                episode["validator_outputs"][0]["result"] = "FAIL"
                episode.update(functional_solve=False, false_completion=True)
        comparison = self.compare(episodes)
        self.assertTrue(comparison["publication_ready"])
        self.assertEqual(comparison["treatment_fsr"], 0.0)

    def test_honest_invalid_pairs_remain_visible_but_outside_denominators(self):
        episodes = repository_episodes(runs=6)
        for episode in episodes:
            if episode["run_index"] == 6:
                episode["validator_outputs"][0]["result"] = "INVALID"
                episode.update(infrastructure_failure=True, functional_solve=False,
                               claimed_success=False, false_completion=False)
        comparison = self.compare(episodes)
        self.assertTrue(comparison["publication_ready"])
        self.assertEqual(comparison["paired_episodes"], 150)

    def test_repository_publish_recomputes_metrics_and_preserves_source_outputs(self):
        episodes = repository_episodes()
        episodes[0]["validator_outputs"][0]["output"] = "private validator detail"
        comparison = self.compare(episodes)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report"
            report_path, _ = bench.report.write_report(
                {}, [comparison], output, publish=True, episodes=episodes,
            )
            text = report_path.read_text()
            self.assertNotIn("RESEARCH PREVIEW", text)
            self.assertIn("| base | 150 |", text)
            self.assertNotIn("private validator detail", (output / "episodes.jsonl").read_text())
            self.assertEqual(episodes[0]["validator_outputs"][0]["output"], "private validator detail")

    def test_published_report_requires_raw_episodes(self):
        comparison = self.compare(repository_episodes())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report"
            with self.assertRaisesRegex(ValueError, "raw episodes"):
                bench.report.write_report({}, [comparison], output, publish=True)
            self.assertFalse(output.exists())

    def test_schema_accepts_new_fields_and_rejects_invalid_evidence_kind(self):
        from jsonschema import Draft7Validator
        schema = json.loads((ROOT / "benchmarks/runner/episode.schema.json").read_text())
        episode = repository_episodes(1, 1)[0]
        self.assertEqual(bench.validate.episode_errors(episode, schema, Draft7Validator), [])
        episode["evidence_kind"] = "unsupported"
        self.assertTrue(bench.validate.episode_errors(episode, schema, Draft7Validator))

    def test_matching_task_and_run_is_not_enough_for_pair_eligibility(self):
        for field in ("model", "repo_commit", "hidden_validator_hash"):
            with self.subTest(field=field):
                episodes = repository_episodes()
                episodes[1][field] = "9" * (64 if field == "hidden_validator_hash" else 40)
                self.assertFalse(self.compare(episodes)["publication_ready"])
        for field in ("fixture_hash", "model_revision", "host_revision", "evaluator_revision"):
            with self.subTest(field=field):
                episodes = repository_episodes()
                episodes[1]["provenance"][field] = "9" * 64
                self.assertFalse(self.compare(episodes)["publication_ready"])

    def test_mixed_configuration_revisions_are_not_one_experiment(self):
        episodes = repository_episodes()
        episodes[2]["provenance"]["configuration_hash"] = "8" * 64
        self.assertFalse(self.compare(episodes)["publication_ready"])

    def test_unpaired_valid_episode_blocks_publication(self):
        episodes = repository_episodes()
        extra = copy.deepcopy(episodes[0])
        extra["run_index"] = 6
        episodes.append(extra)
        self.assertFalse(self.compare(episodes)["publication_ready"])

    def test_duplicate_identity_is_rejected_instead_of_overwritten(self):
        episodes = repository_episodes(1, 1)
        episodes.append(copy.deepcopy(episodes[0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.compare(episodes)

    def test_invalid_run_index_is_not_a_distinct_repetition(self):
        for index in (True, "1", 0, -1):
            with self.subTest(index=index):
                episodes = repository_episodes(1, 1)
                episodes[0]["run_index"] = index
                with self.assertRaisesRegex(ValueError, "run_index"):
                    self.compare(episodes)

    def test_forged_outcome_cannot_clear_publication_gate(self):
        episodes = repository_episodes()
        episodes[0]["validator_outputs"][0]["result"] = "FAIL"
        self.assertFalse(self.compare(episodes)["publication_ready"])

    def test_malformed_invalid_episode_cannot_be_ignored_for_publication(self):
        episodes = repository_episodes()
        extra = copy.deepcopy(episodes[0])
        extra.update(run_index=6, infrastructure_failure=True)
        partner = copy.deepcopy(extra)
        partner["configuration"] = "treated"
        episodes.extend([extra, partner])
        self.assertFalse(self.compare(episodes)["publication_ready"])

    def test_report_with_uncompared_configuration_stays_preview_only(self):
        comparison = self.compare(repository_episodes())
        extra = bench.run.build_episode({"task_id": "PL-001", "commit": "fixture"},
                                        "model", "uncompared-smoke", "1. Inspect", {}, 0.1)
        summary = bench.metrics.aggregate([extra])
        self.assertIn("RESEARCH PREVIEW", bench.report.render_markdown(summary, [comparison]))
        with self.assertRaisesRegex(ValueError, "publication gate"):
            bench.report.render_markdown(summary, [comparison], publish=True)

    def test_write_report_rechecks_episodes_instead_of_trusting_comparison_flag(self):
        comparison = self.compare(repository_episodes())
        episodes = repository_episodes()
        episodes[0]["evidence_kind"] = "smoke"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report"
            with self.assertRaisesRegex(ValueError, "publication gate"):
                bench.report.write_report({}, [comparison], output, publish=True, episodes=episodes)
            self.assertFalse(output.exists())

    def test_unstructured_legacy_readiness_flag_is_not_sufficient(self):
        self.assertFalse(bench.report.publication_ready([{
            "paired_episodes": 150, "publication_ready": True,
        }]))

    def test_preview_still_renders_and_explains_blockers(self):
        comparison = self.compare(repository_episodes(1, 1))
        text = bench.report.render_markdown({}, [comparison])
        self.assertIn("RESEARCH PREVIEW", text)
        self.assertIn("Publication blockers", text)

    def test_publish_failure_creates_no_report_directory(self):
        comparison = self.compare(repository_episodes(1, 1))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "must-not-exist"
            with self.assertRaisesRegex(ValueError, "publication gate"):
                bench.report.write_report({}, [comparison], output, publish=True)
            self.assertFalse(output.exists())

    def test_cli_reports_publication_failure_without_traceback_or_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            episodes = root / "episodes"
            episodes.mkdir()
            for index, episode in enumerate(repository_episodes(1, 1)):
                (episodes / f"{index}.json").write_text(json.dumps(episode))
            output = root / "report"
            with patch.object(bench.compare, "bootstrap_delta", return_value=[0.0, 0.0]):
                result = bench.benchmark_cli.main([
                    "report", "--episodes", str(episodes), "--out", str(output),
                    "--baseline", "base", "--treatment", "treated", "--publish",
                ])
            self.assertEqual(result, 2)
            self.assertFalse(output.exists())


class ClaimsRegistryTests(unittest.TestCase):
    def run_gate(self, readme, manifest):
        def read(path, *args, **kwargs):
            if path.name == "README.md":
                return readme
            if path.name == "manifest.yaml":
                return manifest
            raise AssertionError(f"unexpected read: {path}")
        with patch.object(Path, "read_text", read), redirect_stdout(io.StringIO()):
            runpy.run_path(str(ROOT / "scripts" / "check_readme_claims.py"), run_name="__main__")

    def test_registry_disclosure_uses_actual_lane_tasks(self):
        readme = ("Research preview: comparative performance is not yet measured.\n"
                  "GRAVITAS changes the engineering process, not model weights.\n"
                  "3 registered task specifications across 2 planned lanes\n")
        manifest = "meta:\n  task_count: 3\nlanes:\n  L1:\n    tasks: [A, B]\n  L2:\n    tasks: [C]\n"
        self.run_gate(readme, manifest)

    def test_stale_count_disclosure_is_rejected(self):
        readme = ("Research preview: comparative performance is not yet measured.\n"
                  "GRAVITAS changes the engineering process, not model weights.\n"
                  "30 registered task specifications across 10 planned lanes\n")
        manifest = "meta:\n  task_count: 1\nlanes:\n  L1:\n    tasks: [A]\n"
        with self.assertRaisesRegex(SystemExit, "1 registered task specifications across 1 planned lanes"):
            self.run_gate(readme, manifest)


if __name__ == "__main__":
    unittest.main()
