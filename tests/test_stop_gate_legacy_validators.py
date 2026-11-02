"""Legacy required_validators must match exactly, not by substring."""
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "plugins/gravitas-antigravity/scripts"))

from stop_gate import legacy_requirement_met


ECHO_COMMAND = [sys.executable, "-c", "print('latest')"]


class LegacyRequirementMatchTests(unittest.TestCase):
    def test_substring_of_command_does_not_satisfy(self):
        entry = {"validator_id": "VAL-001", "command": ECHO_COMMAND}
        self.assertFalse(legacy_requirement_met("test", entry))
        self.assertFalse(legacy_requirement_met("echo", entry))

    def test_exact_command_line_satisfies(self):
        entry = {"validator_id": "VAL-001", "command": ["pytest", "-q"]}
        self.assertTrue(legacy_requirement_met("pytest -q", entry))
        self.assertTrue(legacy_requirement_met(shlex.join(entry["command"]), entry))

    def test_validator_id_satisfies(self):
        self.assertTrue(legacy_requirement_met("VAL-001", {"validator_id": "VAL-001", "command": ["x"]}))

    def test_malformed_commands_never_match_or_crash(self):
        for command in (None, "pytest", ["pytest", 1], 7, {}):
            with self.subTest(command=command):
                self.assertFalse(legacy_requirement_met("pytest", {"command": command}))
        self.assertFalse(legacy_requirement_met("", {"command": ["x"]}))
        self.assertFalse(legacy_requirement_met(None, {"command": ["x"]}))


def run_script(name, payload, *args, cwd):
    return subprocess.run(
        [sys.executable, str(ROOT / "plugins/gravitas-antigravity/scripts" / name), *args],
        input=json.dumps(payload) if payload is not None else None,
        text=True, capture_output=True, cwd=cwd, check=False,
    )


class StopGateLegacyValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def init(self, contract):
        result = run_script("init_session.py", None, "--task-id", "test-task",
                            "--contract-json", json.dumps(contract), cwd=self.cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.cwd / json.loads(result.stdout)["session_dir"]

    def _session(self, required):
        return self.init({
            "mode": "implement", "objective": "x",
            "acceptance_criteria": [{"id": "AC1", "statement": "AC1", "validators": ["unit"]}],
            "validators": [{"id": "unit", "command": ECHO_COMMAND, "criterion_ids": ["AC1"]}],
            "required_validators": required,
        })

    def _run_validator(self, session):
        result = run_script(
            "validator_runner.py", None, "--session-dir", str(session), "--validator-id", "unit",
            "--criterion-id", "AC1", "--", *ECHO_COMMAND, cwd=self.cwd)
        self.assertEqual(result.returncode, 0, result.stderr)

    def _decision(self):
        return json.loads(run_script("stop_gate.py", {}, cwd=self.cwd).stdout)

    def test_substring_requirement_is_not_satisfied_by_echo_latest(self):
        session = self._session(["test"])
        self._run_validator(session)
        decision = self._decision()
        self.assertEqual(decision["decision"], "continue")
        self.assertIn("test", decision["reason"])

    def test_exact_declared_command_still_satisfies_requirement(self):
        session = self._session([shlex.join(ECHO_COMMAND)])
        self._run_validator(session)
        self.assertEqual(self._decision()["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
