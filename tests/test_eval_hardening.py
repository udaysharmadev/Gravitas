#!/usr/bin/env python3
"""Eval hardening tests: trace-based grading, trigger negatives, tier eval."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_scorer():
    import importlib.util
    path = ROOT / "eval/scoring/scorer.py"
    spec = importlib.util.spec_from_file_location("hardening_scorer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TraceGradingTests(unittest.TestCase):
    def test_read_before_write_same_file(self):
        m = _load_scorer()
        run_ok = m.TaskRun(task_id="T", condition="c", run=1)
        run_ok.tool_calls = [
            m.ToolCall(tool="read", args={"file": "src/auth.ts"}),
            m.ToolCall(tool="edit", args={"file": "src/auth.ts"}),
        ]
        run_bad = m.TaskRun(task_id="T", condition="c", run=2)
        run_bad.tool_calls = [
            m.ToolCall(tool="edit", args={"file": "src/auth.ts"}),
        ]
        self.assertEqual(m.compute_recon_rate([run_ok]), 1.0)
        self.assertEqual(m.compute_recon_rate([run_bad]), 0.0)

    def test_exact_retry_counts_once(self):
        m = _load_scorer()
        run = m.TaskRun(task_id="T", condition="c", run=1)
        run.tool_calls = [
            m.ToolCall(tool="bash", args={"command": "pytest"}, output="FAILED error"),
            m.ToolCall(tool="bash", args={"command": "pytest"}, output="FAILED error"),
            m.ToolCall(tool="bash", args={"command": "pytest -k other"}, output="ok"),
        ]
        # One failure followed by byte-identical retry => 1 retry / 2 failures = 0.5
        self.assertEqual(m.compute_failure_repetition_rate([run]), 0.5)

    def test_no_mutation_runs_excluded(self):
        m = _load_scorer()
        run = m.TaskRun(task_id="T", condition="c", run=1)
        run.tool_calls = [m.ToolCall(tool="read", args={"file": "a.py"})]
        self.assertEqual(m.compute_recon_rate([run]), 0.0)


class TriggerEvalTests(unittest.TestCase):
    def test_near_miss_negatives_present(self):
        data = json.loads((ROOT / "eval/trigger-eval.json").read_text())
        non = data.get("non_activations", [])
        self.assertGreaterEqual(len(non), 10)
        self.assertTrue(all(item.get("expect") is False for item in non))
        texts = " ".join(item["input"].lower() for item in non)
        self.assertIn("regex", texts)


class TierEvalTests(unittest.TestCase):
    def test_tier_eval_cardinality_and_trap(self):
        data = json.loads((ROOT / "eval/tier-eval.json").read_text())
        cases = data.get("cases", [])
        self.assertGreaterEqual(len(cases), 30)
        by_id = {c["id"]: c for c in cases}
        # Single-file auth change must be deep, not direct.
        auth_singles = [c for c in cases if "single-file" in c["task"].lower() or "single file" in c["task"].lower()]
        self.assertTrue(auth_singles)
        for case in auth_singles:
            if "auth" in case["task"].lower() or "password" in case["task"].lower() or "samesite" in case["task"].lower():
                self.assertEqual(case["expect"], "deep")
        uncertain = [c for c in cases if "uncertain" in c["task"].lower() or "ambiguous" in c["task"].lower()]
        self.assertTrue(uncertain)
        for case in uncertain:
            self.assertEqual(case["expect"], "deep")


class NegativeTaskTests(unittest.TestCase):
    def test_neg_tasks_have_traps(self):
        for task_id in ("NEG-001", "NEG-002", "NEG-003", "NEG-004", "NEG-005"):
            text = (ROOT / "eval/tasks" / f"{task_id}.yaml").read_text()
            self.assertIn("trap:", text)
            self.assertIn("fail_condition:", text)


class LegacyScorerTests(unittest.TestCase):
    def test_no_honest_uncertainty_penalty(self):
        text = (ROOT / "benchmarks/legacy/superseded/benchmark.py").read_text()
        self.assertIn("DEPRECATED", text)
        # The old phrase-score list must be gone; honest uncertainty
        # ("probably", "i think") must not affect scores.
        self.assertNotIn("anti_patterns = [", text)
        self.assertNotIn("5 - violations", text)


if __name__ == "__main__":
    unittest.main()
