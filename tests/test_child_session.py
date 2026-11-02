"""Scoped child sessions: derivation invariants, handoff, parent gate."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins" / "gravitas-antigravity" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import child_session
from child_session import (
    complete_child_handoff,
    derive_child_contract,
    incomplete_children,
    register_child,
)


def run_script(name, payload=None, *args, cwd):
    env = os.environ.copy()
    isolated_home = str(Path(cwd) / ".test-user-home")
    env["HOME"] = isolated_home
    if os.name == "nt":
        env["USERPROFILE"] = isolated_home
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        cwd=cwd,
        env=env,
        check=False,
    )


PARENT = {
    "mode": "implement",
    "objective": "parent task",
    "acceptance_criteria": [
        {"id": "AC1", "statement": "first"},
        {"id": "AC2", "statement": "second"},
    ],
    "allowed_write_scope": ["."],
    "budget": "balanced",
}


def validator_entry(criterion_ids):
    return {
        "source": "validator",
        "validator_id": "unit",
        "criterion_ids": list(criterion_ids),
        "verdict": "PASS",
        "exit_code": 0,
        "event_hash": "abc123",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class DeriveTests(unittest.TestCase):
    def test_valid_child_contract(self):
        child = derive_child_contract(
            PARENT, scope=["."], criteria=["AC1"], mode="implement",
            parent_session="psess",
        )
        self.assertEqual(child["mode"], "implement")
        self.assertEqual(child["allowed_write_scope"], ["."])
        self.assertEqual(child["parent_session"], "psess")

    def test_scope_escape_denied(self):
        parent = dict(PARENT, allowed_write_scope=["src"])
        with self.assertRaisesRegex(ValueError, "escapes parent scope"):
            derive_child_contract(parent, scope=["other"], criteria=["AC1"], mode="implement")

    def test_scope_subset_allowed(self):
        parent = dict(PARENT, allowed_write_scope=["src"])
        child = derive_child_contract(parent, scope=["src/api"], criteria=["AC1"], mode="plan")
        self.assertEqual(child["allowed_write_scope"], ["src/api"])

    def test_read_only_child_of_implement_allowed(self):
        child = derive_child_contract(PARENT, scope=[], criteria=["AC1"], mode="research")
        self.assertEqual(child["mode"], "research")

    def test_mode_escalation_denied(self):
        parent = dict(PARENT, mode="plan")
        with self.assertRaisesRegex(ValueError, "escalation"):
            derive_child_contract(parent, scope=[], criteria=["AC1"], mode="implement")

    def test_unknown_criterion_denied(self):
        with self.assertRaisesRegex(ValueError, "not in the parent contract"):
            derive_child_contract(PARENT, scope=["."], criteria=["AC9"], mode="implement")

    def test_empty_criteria_denied(self):
        with self.assertRaises(ValueError):
            derive_child_contract(PARENT, scope=["."], criteria=[], mode="implement")


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.parent = self.root / "parent"
        self.child = self.root / "child"
        self.parent.mkdir()
        self.child.mkdir()
        (self.parent / "state.json").write_text(json.dumps({}))

    def tearDown(self):
        self.temp.cleanup()

    def test_register_and_duplicate(self):
        register_child(self.parent, "child", ["AC1"])
        self.assertEqual(incomplete_children(self.parent), ["child"])
        with self.assertRaisesRegex(ValueError, "already registered"):
            register_child(self.parent, "child", ["AC1"])

    def test_handoff_requires_child_evidence(self):
        register_child(self.parent, "child", ["AC1"])
        (self.child / "contract.json").write_text(json.dumps({
            "mode": "implement", "objective": "x",
            "acceptance_criteria": [{"id": "AC1", "statement": "first"}],
        }))
        (self.child / "evidence.jsonl").write_text("")
        with self.assertRaisesRegex(ValueError, "no fresh PASS"):
            complete_child_handoff(self.parent, self.child, ["AC1"])
        self.assertEqual(incomplete_children(self.parent), ["child"])

    def test_handoff_marks_complete_on_fresh_pass(self):
        register_child(self.parent, "child", ["AC1"])
        (self.child / "contract.json").write_text(json.dumps({
            "mode": "implement", "objective": "x",
            "acceptance_criteria": [{"id": "AC1", "statement": "first"}],
        }))
        (self.child / "evidence.jsonl").write_text(json.dumps(validator_entry(["AC1"])) + "\n")
        complete_child_handoff(self.parent, self.child, ["AC1"])
        self.assertEqual(incomplete_children(self.parent), [])

    def test_handoff_unregistered_child_denied(self):
        (self.child / "contract.json").write_text(json.dumps({
            "mode": "implement", "objective": "x",
            "acceptance_criteria": [{"id": "AC1", "statement": "first"}],
        }))
        (self.child / "evidence.jsonl").write_text(json.dumps(validator_entry(["AC1"])) + "\n")
        with self.assertRaisesRegex(ValueError, "not registered"):
            complete_child_handoff(self.parent, self.child, ["AC1"])


class ParentGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def init(self, contract, task_id="parent-task"):
        result = run_script(
            "init_session.py", None, "--task-id", task_id,
            "--contract-json", json.dumps(contract), cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.cwd / json.loads(result.stdout)["session_dir"]

    def cover(self, session, criterion):
        result = run_script(
            "validator_runner.py", None, "--session-dir", str(session),
            "--validator-id", "unit", "--criterion-id", criterion,
            "--", sys.executable, "-c", "pass", cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def contract(self, criteria):
        return {
            "mode": "implement", "objective": "x",
            "acceptance_criteria": [
                {"id": c, "statement": c, "validators": ["unit"]} for c in criteria
            ],
            "validators": [{
                "id": "unit",
                "command": [sys.executable, "-c", "pass"],
                "criterion_ids": criteria,
            }],
            "allowed_write_scope": ["."],
        }

    def test_gate_blocks_on_incomplete_child(self):
        session = self.init(self.contract(["AC1", "AC2"]))
        self.cover(session, "AC1")
        self.cover(session, "AC2")
        register_child(session, "child-a", ["AC1"])
        decision = json.loads(run_script("stop_gate.py", {}, cwd=self.cwd).stdout)
        self.assertEqual(decision["decision"], "continue")
        self.assertIn("child-a", decision["reason"])

    def test_gate_allows_after_handoff(self):
        session = self.init(self.contract(["AC1", "AC2"]))
        self.cover(session, "AC1")
        self.cover(session, "AC2")
        child_dir = session.parent / "child-a"
        child_dir.mkdir()
        child_contract = derive_child_contract(
            json.loads((session / "contract.json").read_text()),
            scope=["."], criteria=["AC1"], mode="implement",
            parent_session=session.name,
        )
        child_contract["validators"] = [{
            "id": "unit",
            "command": [sys.executable, "-c", "pass"],
            "criterion_ids": ["AC1"],
        }]
        (child_dir / "contract.json").write_text(json.dumps(child_contract))
        self.cover(child_dir, "AC1")
        register_child(session, "child-a", ["AC1"])
        complete_child_handoff(session, child_dir, ["AC1"])
        decision = json.loads(run_script("stop_gate.py", {}, cwd=self.cwd).stdout)
        self.assertEqual(decision["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
