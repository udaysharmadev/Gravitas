"""Validator `command` is an argv array in both schemas and in the runner."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/gravitas-antigravity/scripts"


def contract_with(command):
    return {"mode": "implement", "objective": "x", "validators": [{"id": "VAL-001", "command": command}]}


class SchemaAgreementTests(unittest.TestCase):
    def test_contract_schema_accepts_array_and_rejects_string(self):
        schema = json.loads((ROOT / "schemas/contract.json").read_text())
        validator = Draft7Validator(schema)
        for command, ok in ((["pytest", "-q"], True), ("pytest -q", False), ([], False)):
            with self.subTest(command=command):
                errors = [e for e in validator.iter_errors(contract_with(command)) if "validators" in list(e.absolute_path)]
                self.assertEqual(not errors, ok, [e.message for e in errors])

    def test_both_schemas_use_the_same_command_type(self):
        contract = json.loads((ROOT / "schemas/contract.json").read_text())
        task = json.loads((ROOT / "schemas/task-contract.schema.json").read_text())
        a = contract["properties"]["validators"]["items"]["properties"]["command"]["type"]
        b = task["properties"]["validators"]["items"]["properties"]["command"]["type"]
        self.assertEqual(a, b)
        self.assertEqual(a, "array")


class RunnerStringCommandTests(unittest.TestCase):
    def run_runner(self, declared):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            init = subprocess.run(
                [sys.executable, str(SCRIPTS / "init_session.py"), "--task-id", "t",
                 "--contract-json", json.dumps({"mode": "implement", "objective": "x"})],
                text=True, capture_output=True, cwd=cwd, check=False)
            self.assertEqual(init.returncode, 0, init.stderr)
            session = cwd / json.loads(init.stdout)["session_dir"]
            (session / "contract.json").write_text(json.dumps(contract_with(declared)))
            return subprocess.run(
                [sys.executable, str(SCRIPTS / "validator_runner.py"), "--session-dir", str(session),
                 "--validator-id", "VAL-001", "--", sys.executable, "-c", "pass"],
                text=True, capture_output=True, cwd=cwd, check=False)

    def test_string_command_gets_a_clear_error(self):
        result = self.run_runner("pytest -q")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("argv array", result.stderr)
        self.assertNotIn("differs from the contract declaration", result.stderr)

    def test_array_command_still_runs(self):
        result = self.run_runner([sys.executable, "-c", "pass"])
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
