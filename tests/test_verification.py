"""Phase 4 tests: discovery, escalation, evidence states, reproduction."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/gravitas-antigravity/scripts"
sys.path.insert(0, str(SCRIPTS))

import test_runtime
from gravitas_evidence import criterion_states, evidence_deficit
from gravitas_verify import discover_validators, escalation_plan, expand_cases


def make_bin(tmp: Path, name: str) -> None:
    path = tmp / name
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(self.bin)

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        self.temp.cleanup()

    def test_empty_repo_discovers_nothing(self):
        catalog = discover_validators(self.root)
        self.assertEqual(catalog["validators"], [])
        self.assertEqual(catalog["ci"], [])

    def test_python_pytest_discovered_with_provenance(self):
        (self.root / "pyproject.toml").write_text("[tool.pytest]\n")
        (self.root / "tests").mkdir()
        make_bin(self.bin, "pytest")
        catalog = discover_validators(self.root)
        ids = [v["id"] for v in catalog["validators"]]
        self.assertIn("pytest", ids)
        entry = next(v for v in catalog["validators"] if v["id"] == "pytest")
        self.assertTrue(any(p.startswith("config:") for p in entry["provenance"]))
        self.assertTrue(any(p.startswith("binary:") for p in entry["provenance"]))

    def test_config_without_binary_is_omitted(self):
        (self.root / "pyproject.toml").write_text("[tool.pytest]\n")
        (self.root / "tests").mkdir()
        catalog = discover_validators(self.root)
        self.assertNotIn("pytest", [v["id"] for v in catalog["validators"]])

    def test_npm_test_script_becomes_suite_validator(self):
        (self.root / "package.json").write_text(json.dumps({"scripts": {"test": "node run.js"}}))
        make_bin(self.bin, "npm")
        catalog = discover_validators(self.root)
        self.assertIn("npm-test", [v["id"] for v in catalog["validators"]])

    def test_makefile_target_becomes_suite_validator(self):
        (self.root / "Makefile").write_text("test:\n\tpytest -q\n")
        catalog = discover_validators(self.root)
        self.assertIn("make-test", [v["id"] for v in catalog["validators"]])

    def test_ci_workflows_listed(self):
        workflows = self.root / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("on: push\n")
        catalog = discover_validators(self.root)
        self.assertEqual(catalog["ci"], ["ci.yml"])

    def test_repo_with_markers_and_binary_discovers_pytest(self):
        (self.root / "pyproject.toml").write_text("[tool.pytest]\n")
        (self.root / "tests").mkdir()
        make_bin(self.bin, "pytest")
        catalog = discover_validators(self.root)
        self.assertIn("pytest", [v["id"] for v in catalog["validators"]])


class EscalationTests(unittest.TestCase):
    def catalog(self):
        return {"root": "/r", "ci": ["ci.yml"], "validators": [
            {"id": "pytest", "kind": "test", "command": ["pytest", "-q"],
             "provenance": ["config:tests"], "scope": "project"},
            {"id": "ruff", "kind": "lint", "command": ["ruff", "check", "."],
             "provenance": ["config:pyproject.toml"], "scope": "project"},
        ]}

    def test_targeted_always_runs_tests(self):
        plan = escalation_plan(self.catalog(), verification_depth="targeted",
                               changed=["a.py"], related={})
        self.assertEqual(plan["rungs"]["targeted"]["validators"], ["pytest"])
        self.assertEqual(plan["rungs"]["impact"]["validators"], [])
        self.assertEqual(plan["rungs"]["full"]["validators"], [])

    def test_failure_evidence_expands(self):
        plan = escalation_plan(self.catalog(), verification_depth="targeted",
                               changed=["a.py"], related={"a.py": ["b.py"]},
                               failure_evidence=True)
        self.assertEqual(plan["rungs"]["impact"]["files"], ["a.py", "b.py"])
        self.assertIn("pytest", plan["rungs"]["suite"]["validators"])
        self.assertIn("ruff", plan["rungs"]["suite"]["validators"])

    def test_full_depth_without_release_stops_at_suite(self):
        plan = escalation_plan(self.catalog(), verification_depth="full",
                               changed=["a.py"], related={})
        self.assertTrue(plan["rungs"]["suite"]["validators"])
        self.assertEqual(plan["rungs"]["full"]["validators"], [])

    def test_release_runs_everything(self):
        plan = escalation_plan(self.catalog(), verification_depth="full",
                               changed=["a.py"], related={}, release_context=True)
        self.assertTrue(plan["rungs"]["full"]["validators"])
        self.assertEqual(plan["rungs"]["full"]["ci"], ["ci.yml"])


class EvidenceStateTests(unittest.TestCase):
    def contract(self):
        return {"acceptance_criteria": [
            {"id": "AC-1", "statement": "login works"},
            {"id": "AC-2", "statement": "logout works"},
        ]}

    def owned_pass(self, ts):
        return {"source": "validator", "validator_id": "v", "criterion_ids": ["AC-1"],
                "verdict": "PASS", "exit_code": 0, "event_hash": "h1", "timestamp": ts}

    def test_pass_pending_supported(self):
        states = criterion_states(self.contract(), [
            self.owned_pass("2026-10-07T10:00:00+00:00"),
            {"source": "test_run", "criterion_ids": ["AC-2"], "verdict": "PASS",
             "evidence": "pytest 3 passed", "timestamp": "2026-10-07T10:00:00+00:00"},
        ])
        self.assertEqual(states["AC-1"]["status"], "PASS")
        self.assertEqual(states["AC-2"]["status"], "SUPPORTED")
        deficit = evidence_deficit(self.contract(), states)
        self.assertEqual([d["criterion"] for d in deficit], ["AC-2"])
        self.assertIn("Gravitas-owned validator", deficit[0]["needed"])

    def test_stale_pass_blocks(self):
        states = criterion_states(self.contract(), [
            self.owned_pass("2026-10-07T10:00:00+00:00"),
            {"source": "write", "file": "a.py", "timestamp": "2026-10-07T11:00:00+00:00"},
        ])
        self.assertEqual(states["AC-1"]["status"], "PENDING")
        self.assertEqual(states["AC-1"]["stale_owned"], 1)

    def test_latest_fail_wins_over_older_pass(self):
        states = criterion_states(self.contract(), [
            self.owned_pass("2026-10-07T10:00:00+00:00"),
            {**self.owned_pass("2026-10-07T12:00:00+00:00"),
             "verdict": "FAIL", "exit_code": 1},
        ])
        self.assertEqual(states["AC-1"]["status"], "FAIL")

    def test_blocked_and_unverifiable_declared(self):
        contract = {"acceptance_criteria": [
            {"id": "AC-1", "statement": "x", "status": "BLOCKED", "reason": "needs prod db"},
            {"id": "AC-2", "statement": "y"},
        ]}
        states = criterion_states(contract, [
            {"source": "reproducer", "criterion_ids": ["AC-2"], "verdict": "UNVERIFIABLE",
             "evidence": "nope", "timestamp": "2026-10-07T10:00:00+00:00"},
        ])
        self.assertEqual(states["AC-1"]["status"], "BLOCKED")
        self.assertEqual(states["AC-2"]["status"], "UNVERIFIABLE")


class EdgeCaseTests(unittest.TestCase):
    def test_expansion_is_deterministic_and_deduped(self):
        first = expand_cases(["5", "", "5"])
        second = expand_cases(["5", "", "5"])
        self.assertEqual(first, second)
        values = [v["value"] for v in first]
        self.assertEqual(len(values), len(set(values)))

    def test_numeric_and_string_boundaries(self):
        values = [v["value"] for v in expand_cases(["5"])]
        for boundary in ("0", "-1", "2147483647", ""):
            self.assertIn(boundary, values)
        strings = [v["value"] for v in expand_cases(["name"])]
        for boundary in ("", "ünïcodé✓", "' OR '1'='1"):
            self.assertIn(boundary, strings)

    def test_reasons_attached(self):
        for variant in expand_cases(["x"]):
            self.assertTrue(variant["reason"])


class ReproRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def init(self, contract):
        result = test_runtime.run_script(
            "init_session.py", None, "--task-id", "t",
            "--contract-json", json.dumps(contract), cwd=self.cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.cwd / ".gravitas/sessions/t"

    def repro(self, session, criterion, phase, *cmd, unreproducible=False, reason=""):
        args = ["--session-dir", str(session), "--criterion-id", criterion,
                "--phase", phase]
        if unreproducible:
            args += ["--unreproducible", "--reason", reason]
        else:
            args += ["--", *cmd]
        return test_runtime.run_script("repro_runner.py", None, *args, cwd=self.cwd)

    def test_fail_before_pass_after_pair(self):
        session = self.init({"mode": "debug", "objective": "fix it",
                             "acceptance_criteria": [{"id": "AC-1", "statement": "fixed"}]})
        failing = self.repro(session, "AC-1", "before", sys.executable, "-c",
                             "raise SystemExit(1)")
        self.assertNotEqual(failing.returncode, 0)
        passing = self.repro(session, "AC-1", "after", sys.executable, "-c", "pass")
        self.assertEqual(passing.returncode, 0, passing.stderr)
        entries = [json.loads(line) for line in (session / "evidence.jsonl").read_text().splitlines()]
        repro = [e for e in entries if e.get("source") == "reproducer"]
        self.assertEqual([(e["phase"], e["verdict"]) for e in repro],
                         [("before", "FAIL"), ("after", "PASS")])

    def test_undeclared_criterion_rejected(self):
        session = self.init({"mode": "debug", "objective": "x",
                             "acceptance_criteria": [{"id": "AC-1", "statement": "y"}]})
        result = self.repro(session, "NOPE", "before", sys.executable, "-c", "pass")
        self.assertNotEqual(result.returncode, 0)

    def test_unreproducible_blocks_gate(self):
        session = self.init({"mode": "debug", "objective": "x",
                             "acceptance_criteria": [{"id": "AC-1", "statement": "y"}]})
        result = self.repro(session, "AC-1", "before", unreproducible=True,
                            reason="needs production hardware")
        self.assertEqual(result.returncode, 0, result.stderr)
        gate = json.loads(test_runtime.run_script("stop_gate.py", {}, cwd=self.cwd).stdout)
        self.assertEqual(gate["decision"], "continue")
        self.assertIn("y", gate["reason"])

    def test_stale_validator_evidence_blocks_gate(self):
        session = self.init({
            "mode": "implement", "objective": "x",
            "acceptance_criteria": [{"id": "AC-1", "statement": "y", "validators": ["unit"]}],
            "validators": [{"id": "unit", "command": [sys.executable, "-c", "pass"],
                           "criterion_ids": ["AC-1"]}],
        })
        run = test_runtime.run_script(
            "validator_runner.py", None, "--session-dir", str(session),
            "--validator-id", "unit", "--criterion-id", "AC-1",
            "--", sys.executable, "-c", "pass", cwd=self.cwd)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(
            json.loads(test_runtime.run_script("stop_gate.py", {}, cwd=self.cwd).stdout)["decision"],
            "allow")
        (session / "evidence.jsonl").write_text(
            (session / "evidence.jsonl").read_text() + json.dumps({
                "source": "write", "file": "a.py",
                "timestamp": "2999-01-01T00:00:00+00:00"}) + "\n")
        gate = json.loads(test_runtime.run_script("stop_gate.py", {}, cwd=self.cwd).stdout)
        self.assertEqual(gate["decision"], "continue")

    def test_reproducer_entry_validates_against_schema(self):
        from jsonschema import Draft7Validator
        session = self.init({"mode": "debug", "objective": "x",
                             "acceptance_criteria": [{"id": "AC-1", "statement": "y"}]})
        self.repro(session, "AC-1", "before", sys.executable, "-c", "pass")
        schema = json.loads((ROOT / "schemas/evidence.schema.json").read_text())
        entries = [json.loads(line) for line in (session / "evidence.jsonl").read_text().splitlines()]
        Draft7Validator(schema).validate(
            next(e for e in entries if e.get("source") == "reproducer"))


if __name__ == "__main__":
    unittest.main()
