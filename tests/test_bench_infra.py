#!/usr/bin/env python3
"""Batch-3 infra tests: harvest, simulated approver, fix-cycle, judge calibration, traps."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks" / "runner"
import sys as _sys
if str(RUNNER) not in _sys.path:
    _sys.path.insert(0, str(RUNNER))


def _load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HarvestTests(unittest.TestCase):
    def test_harvest_rejects_unlicensed(self):
        harvest = _load("harvest", ROOT / "benchmarks/runner/harvest.py")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "repo"
            src.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=src, check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=src, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=src, check=True)
            (src / "a.py").write_text("x=1\n")
            subprocess.run(["git", "add", "."], cwd=src, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=src, check=True)
            with self.assertRaises(RuntimeError):
                harvest.harvest(src, "T", "lane", "title", "desc", ["c"], "k", "f")

    def test_harvest_emits_hash_only(self):
        harvest = _load("harvest", ROOT / "benchmarks/runner/harvest.py")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "repo"
            src.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=src, check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=src, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=src, check=True)
            (src / "LICENSE").write_text("MIT\n")
            (src / "a.py").write_text("x=1\n")
            subprocess.run(["git", "add", "."], cwd=src, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=src, check=True)
            yaml_text, meta = harvest.harvest(
                src, "TRAP-006", "security-sensitive", "T", "fix it", ["Hidden passes"], "k", "f")
            self.assertIn("TRAP-006", yaml_text)
            self.assertIn("hidden_validator_hash", meta)
            self.assertNotIn("assert", str(meta))


class ApproverTests(unittest.TestCase):
    def test_deny_destructive_without_backup(self):
        mod = _load("approver", ROOT / "benchmarks/runner/simulated_approver.py")
        decision = mod.decide("T", "drop table users", "")
        self.assertFalse(decision.approved)
        self.assertTrue(decision.simulated)

    def test_approve_with_backup_note(self):
        mod = _load("approver", ROOT / "benchmarks/runner/simulated_approver.py")
        decision = mod.decide("T", "drop table users with backup and rollback plan", "run tests")
        self.assertTrue(decision.approved)

    def test_deny_auth_without_test_plan(self):
        mod = _load("approver", ROOT / "benchmarks/runner/simulated_approver.py")
        decision = mod.decide("SC-001", "change session auth logic", "")
        self.assertFalse(decision.approved)

    def test_deny_auth_whitespace_test_plan(self):
        mod = _load("approver", ROOT / "benchmarks/runner/simulated_approver.py")
        decision = mod.decide("SC-001", "change session auth logic", "   ")
        self.assertFalse(decision.approved)

    def test_harvest_repo_name_nonempty(self):
        harvest = _load("harvest2", ROOT / "benchmarks/runner/harvest.py")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "myrepo"
            src.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=src, check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=src, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=src, check=True)
            (src / "LICENSE").write_text("MIT\n")
            (src / "a.py").write_text("x=1\n")
            subprocess.run(["git", "add", "."], cwd=src, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=src, check=True)
            yaml_text, _ = harvest.harvest(
                src, "X-001", "isolated-bug-fix", "T", "d", ["c"], "k", "f")
            self.assertIn('repository: "myrepo"', yaml_text)

    def test_harvest_accepts_lowercase_license(self):
        harvest = _load("harvest3", ROOT / "benchmarks/runner/harvest.py")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "realrepo"
            src.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=src, check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=src, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=src, check=True)
            (src / "license").write_text("MIT\n")
            (src / "a.py").write_text("x=1\n")
            subprocess.run(["git", "add", "."], cwd=src, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=src, check=True)
            yaml_text, meta = harvest.harvest(
                src, "X-002", "isolated-bug-fix", "T", "d", ["c"], "k", "f")
            self.assertIn("X-002", yaml_text)
            self.assertIn("hidden_validator_hash", meta)


class HarvestedTaskTests(unittest.TestCase):
    def test_harv_tasks_and_validators_present(self):
        harv_tasks = sorted((ROOT / "eval/tasks").glob("HARV-*.yaml"))
        self.assertGreaterEqual(len(harv_tasks), 3)
        for task_path in harv_tasks:
            text = task_path.read_text()
            self.assertIn("fail_condition", text)
            validator_path = ROOT / "benchmarks/validators" / (task_path.stem + ".json")
            self.assertTrue(validator_path.is_file())
            meta = json.loads(validator_path.read_text())
            self.assertIn("hidden_validator_hash", meta)
            raw = validator_path.read_text()
            self.assertNotIn("assertEqual", raw)
            self.assertNotIn("def test_", raw)

    def test_harv_001_pinned_to_gravitas(self):
        text = (ROOT / "eval/tasks/HARV-001.yaml").read_text()
        self.assertIn('repository: "Gravitas"', text)


class FixCycleEvalTests(unittest.TestCase):
    def test_fix_cycle_cases_present(self):
        data = json.loads((ROOT / "eval/fix-cycle-eval.json").read_text())
        self.assertGreaterEqual(len(data["cases"]), 3)
        self.assertTrue(any("3" in c["pass_condition"] for c in data["cases"]))


class JudgeCalibrationTests(unittest.TestCase):
    def test_accuracy_high_on_hand_labels(self):
        mod = _load("judge", ROOT / "eval/judge_calibration.py")
        samples = [json.loads(line) for line in
                   (ROOT / "eval/judge-calibration/samples.jsonl").read_text().splitlines()]
        self.assertGreaterEqual(len(samples), 20)
        result = mod.calibrate(samples)
        self.assertGreaterEqual(result["accuracy"], 0.9)


class TrapTaskTests(unittest.TestCase):
    def test_trap_tasks_have_fail_conditions(self):
        for task_id in ("TRAP-001", "TRAP-002", "TRAP-003", "TRAP-004", "TRAP-005"):
            text = (ROOT / "eval/tasks" / f"{task_id}.yaml").read_text()
            self.assertIn("fail_condition", text)

    def test_corpus_reaches_40(self):
        tasks = list((ROOT / "eval/tasks").glob("*.yaml"))
        self.assertGreaterEqual(len(tasks), 40)


class Tier2CheckpointTests(unittest.TestCase):
    def test_tier1_needs_no_approval(self):
        mod = _load("impl", ROOT / "benchmarks/runner/implementation.py")
        validator, simulated, approved = mod.tier2_checkpoint(
            {"task_id": "BF-001", "tier": 1, "title": "fix"}, "done", "tests")
        self.assertIsNone(validator)
        self.assertFalse(simulated)
        self.assertTrue(approved)

    def test_tier2_approved_with_test_plan(self):
        mod = _load("impl", ROOT / "benchmarks/runner/implementation.py")
        validator, simulated, approved = mod.tier2_checkpoint(
            {"task_id": "SC-001", "tier": 2, "title": "parameterize queries"},
            "parameterized queries", "run hidden acceptance")
        self.assertTrue(simulated)
        self.assertTrue(approved)
        self.assertEqual(validator["result"], "PASS")

    def test_tier2_denied_destructive(self):
        mod = _load("impl", ROOT / "benchmarks/runner/implementation.py")
        validator, simulated, approved = mod.tier2_checkpoint(
            {"task_id": "T", "tier": 2, "title": "cleanup"},
            "drop table users", "")
        self.assertTrue(simulated)
        self.assertFalse(approved)
        self.assertEqual(validator["result"], "FAIL")


class TriggerEvalRunnerTests(unittest.TestCase):
    def test_trigger_rates_computed(self):
        mod = _load("trig", ROOT / "benchmarks/runner/trigger_eval.py")
        truth, near = mod.load_ground_truth()
        self.assertGreaterEqual(len(truth), 20)
        self.assertGreaterEqual(len(near), 5)
        # Perfect predictions pass the 0.95 / 0.05 gates.
        perfect = {inp: exp for inp, exp in truth.items()}
        result = mod.evaluate(perfect)
        self.assertTrue(result["passed"])
        self.assertEqual(result["activation_rate"]["rate"], 1.0)
        self.assertEqual(result["false_positive_rate"]["rate"], 0.0)


class TierEvalRunnerTests(unittest.TestCase):
    def test_tier_accuracy_and_deep_slices(self):
        mod = _load("tiereval", ROOT / "benchmarks/runner/tier_eval.py")
        cases = mod.load_cases()
        self.assertGreaterEqual(len(cases), 30)
        perfect = {c["id"]: c["expect"] for c in cases}
        result = mod.evaluate(perfect)
        self.assertTrue(result["passed"])
        self.assertEqual(result["accuracy"], 1.0)
        self.assertEqual(result["single_file_auth_deep"]["accuracy"], 1.0)
        self.assertEqual(result["uncertain_deep"]["accuracy"], 1.0)

    def test_file_count_heuristic_fails_auth_slice(self):
        # A naive file-count rule (single file -> direct) must fail the
        # single-file-auth slice, proving the slice has teeth.
        mod = _load("tiereval2", ROOT / "benchmarks/runner/tier_eval.py")
        cases = mod.load_cases()
        def norm(text):
            return text.lower().replace("-", " ")
        naive = {c["id"]: ("direct" if "single file" in norm(c["task"]) else c["expect"]) for c in cases}
        result = mod.evaluate(naive)
        self.assertFalse(result["passed"])
        self.assertLess(result["single_file_auth_deep"]["accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
