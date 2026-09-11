import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft7Validator, ValidationError


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/gravitas-antigravity/scripts"


def run_script(name, payload=None, *args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        cwd=cwd,
        check=False,
    )


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def init(self, contract, task_id="test-task", conversation_id=None):
        args = ["--task-id", task_id, "--contract-json", json.dumps(contract)]
        if conversation_id:
            args.extend(["--conversation-id", conversation_id])
        result = run_script(
            "init_session.py", None, *args, cwd=self.cwd
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.cwd / json.loads(result.stdout)["session_dir"]

    def test_init_creates_recovery_cache_and_coverage(self):
        session = self.init({"mode": "implement", "objective": "x", "acceptance_criteria": ["AC1"]})
        state = json.loads((session / "state.json").read_text())
        self.assertEqual(state["read_files"], [])
        self.assertEqual(json.loads((session / "coverage.json").read_text()), {"AC1": "PENDING"})

    def test_init_rejects_task_id_path_traversal(self):
        result = run_script(
            "init_session.py", None,
            "--task-id", "../escape", "--contract-json", json.dumps({"mode": "implement", "objective": "x"}),
            cwd=self.cwd,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.cwd.parent / "escape").exists())

    def test_plan_only_blocks_shell_mutation(self):
        self.init({"mode": "plan-only", "objective": "x"})
        result = run_script("pre_tool.py", {"toolCall": {"name": "run_command", "args": {"CommandLine": "git commit -m nope"}}}, cwd=self.cwd)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_scope_uses_path_boundaries(self):
        self.init({"mode": "implement", "objective": "x", "allowed_write_scope": ["src/api"]})
        result = run_script("pre_tool.py", {"tool_name": "write_to_file", "tool_input": {"TargetFile": "src/api-evil/x.py"}}, cwd=self.cwd)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_absolute_read_allows_relative_write_and_new_file(self):
        session = self.init({"mode": "implement", "objective": "x"})
        target = self.cwd / "existing.py"
        target.write_text("x = 1\n")
        (session / "evidence.jsonl").write_text(json.dumps({"source": "read", "file": str(target)}) + "\n")
        existing = run_script("pre_tool.py", {"tool_name": "write_to_file", "tool_input": {"TargetFile": "existing.py"}}, cwd=self.cwd)
        new = run_script("pre_tool.py", {"tool_name": "write_to_file", "tool_input": {"TargetFile": "new.py"}}, cwd=self.cwd)
        self.assertEqual(json.loads(existing.stdout)["decision"], "allow")
        self.assertEqual(json.loads(new.stdout)["decision"], "allow")

    def test_destructive_command_requires_confirmation(self):
        self.init({"mode": "implement", "objective": "x"})
        result = run_script("pre_tool.py", {"tool_name": "run_command", "tool_input": {"CommandLine": "rm stale.txt"}}, cwd=self.cwd)
        self.assertEqual(json.loads(result.stdout)["decision"], "force_ask")

    def test_model_supplied_confirmation_cannot_bypass_destructive_prompt(self):
        self.init({"mode": "implement", "objective": "x"})
        payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": "rm stale.txt", "confirmed": True}}}
        result = run_script("pre_tool.py", payload, cwd=self.cwd)
        self.assertEqual(json.loads(result.stdout)["decision"], "force_ask")

    def test_existing_write_without_session_is_denied(self):
        (self.cwd / "existing.py").write_text("VALUE = 1\n")
        payload = {"toolCall": {"name": "write_to_file", "args": {"TargetFile": "existing.py"}}}
        result = run_script("pre_tool.py", payload, cwd=self.cwd)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_official_post_tool_payload_records_read_and_returns_json(self):
        session = self.init({"mode": "implement", "objective": "x"})
        target = self.cwd / "module.py"
        target.write_text("VALUE = 1\n")
        payload = {
            "toolCall": {"name": "view_file", "args": {"AbsolutePath": str(target)}},
            "error": "",
        }
        result = run_script("post_tool.py", payload, cwd=self.cwd)
        self.assertEqual(json.loads(result.stdout), {})
        entries = [json.loads(line) for line in (session / "evidence.jsonl").read_text().splitlines()]
        self.assertEqual(entries[-1]["source"], "read")
        self.assertEqual(entries[-1]["file"], str(target))
        schema = json.loads((ROOT / "schemas/evidence.schema.json").read_text())
        Draft7Validator(schema).validate(entries[-1])

    def test_invalid_pre_tool_payload_denies_fail_closed(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "pre_tool.py")],
            input="not-json",
            text=True,
            capture_output=True,
            cwd=self.cwd,
            check=False,
        )
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_structurally_invalid_pre_tool_payload_denies_fail_closed(self):
        result = run_script("pre_tool.py", {"toolCall": {"name": "run_command", "args": "not-an-object"}}, cwd=self.cwd)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_command_evidence_is_schema_complete(self):
        session = self.init({"mode": "implement", "objective": "x"})
        payload = {
            "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest -q"}},
            "tool_output": "1 passed",
            "success": True,
        }
        result = run_script("post_tool.py", payload, cwd=self.cwd)
        self.assertEqual(json.loads(result.stdout), {})
        entries = [json.loads(line) for line in (session / "evidence.jsonl").read_text().splitlines()]
        schema = json.loads((ROOT / "schemas/evidence.schema.json").read_text())
        Draft7Validator(schema).validate(entries[-1])
        with self.assertRaises(ValidationError):
            Draft7Validator(schema).validate({"source": "test_run", "timestamp": "2026-01-01T00:00:00Z"})

    def test_validator_runner_records_hash_linked_exit_code_evidence(self):
        session = self.init({
            "mode": "implement", "objective": "x",
            "acceptance_criteria": [{"id": "tests", "statement": "tests pass", "validators": ["unit"]}],
            "validators": [{"id": "unit", "command": [sys.executable, "-c", "pass"], "criterion_ids": ["tests"]}],
        })
        result = run_script(
            "validator_runner.py", None, "--session-dir", str(session), "--validator-id", "unit",
            "--criterion-id", "tests", "--", sys.executable, "-c", "pass", cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = json.loads((session / "evidence.jsonl").read_text().splitlines()[-1])
        self.assertEqual(entry["exit_code"], 0)
        self.assertEqual(entry["validator_id"], "unit")
        self.assertIn("event_hash", entry)
        self.assertEqual(json.loads(run_script("stop_gate.py", {}, cwd=self.cwd).stdout)["decision"], "allow")

    def test_chain_verifier_detects_tampering(self):
        session = self.init({
            "mode": "implement", "objective": "x",
            "validators": [{"id": "unit", "command": [sys.executable, "-c", "pass"]}],
        })
        result = run_script("validator_runner.py", None, "--session-dir", str(session), "--validator-id", "unit", "--", sys.executable, "-c", "pass", cwd=self.cwd)
        self.assertEqual(result.returncode, 0)
        ledger = session / "evidence.jsonl"
        ledger.write_text(ledger.read_text().replace('"exit_code":0', '"exit_code":1'))
        cli = subprocess.run([sys.executable, str(ROOT / "gravitas_cli.py"), "verify", "--session-dir", str(session)], text=True, capture_output=True, cwd=self.cwd, check=False)
        self.assertNotEqual(cli.returncode, 0)

    def test_validator_runner_rejects_undeclared_criterion_or_command(self):
        session = self.init({
            "mode": "implement", "objective": "x",
            "acceptance_criteria": [{"id": "unit", "statement": "unit passes", "validators": ["unit"]}],
            "validators": [{"id": "unit", "command": [sys.executable, "-c", "pass"], "criterion_ids": ["unit"]}],
        })
        wrong_criterion = run_script("validator_runner.py", None, "--session-dir", str(session), "--validator-id", "unit", "--criterion-id", "other", "--", sys.executable, "-c", "pass", cwd=self.cwd)
        wrong_command = run_script("validator_runner.py", None, "--session-dir", str(session), "--validator-id", "unit", "--criterion-id", "unit", "--", sys.executable, "-c", "print('not declared')", cwd=self.cwd)
        self.assertNotEqual(wrong_criterion.returncode, 0)
        self.assertIn("unknown structured criterion", wrong_criterion.stderr)
        self.assertNotEqual(wrong_command.returncode, 0)
        self.assertIn("differs from the contract", wrong_command.stderr)

    def test_official_hook_telemetry_cannot_complete_a_contract(self):
        session = self.init({"mode": "implement", "objective": "x", "acceptance_criteria": ["AC1"]})
        payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": "pytest -q"}}, "error": ""}
        self.assertEqual(run_script("post_tool.py", payload, cwd=self.cwd).returncode, 0)
        decision = json.loads(run_script("stop_gate.py", {}, cwd=self.cwd).stdout)
        self.assertEqual(decision["decision"], "continue")

    def test_native_conversation_without_contract_fails_closed_for_shell(self):
        payload = {"conversationId": "uninitialized", "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest -q"}}}
        decision = json.loads(run_script("pre_tool.py", payload, cwd=self.cwd).stdout)
        self.assertEqual(decision["decision"], "deny")

    def test_conversation_ids_isolate_read_before_write_state(self):
        first = self.init({"mode": "implement", "objective": "first"}, task_id="first", conversation_id="conversation-a")
        second = self.init({"mode": "implement", "objective": "second"}, task_id="second", conversation_id="conversation-b")
        target = self.cwd / "existing.py"
        target.write_text("VALUE = 1\n")
        (first / "evidence.jsonl").write_text(json.dumps({"source": "read", "file": str(target)}) + "\n")
        first_payload = {"conversationId": "conversation-a", "toolCall": {"name": "write_to_file", "args": {"TargetFile": "existing.py"}}}
        second_payload = {"conversationId": "conversation-b", "toolCall": {"name": "write_to_file", "args": {"TargetFile": "existing.py"}}}
        self.assertEqual(json.loads(run_script("pre_tool.py", first_payload, cwd=self.cwd).stdout)["decision"], "allow")
        self.assertEqual(json.loads(run_script("pre_tool.py", second_payload, cwd=self.cwd).stdout)["decision"], "deny")
        self.assertNotEqual(first, second)

    def test_post_tool_redacts_secrets_before_persisting(self):
        session = self.init({"mode": "implement", "objective": "x"}, conversation_id="private-conversation")
        payload = {
            "conversationId": "private-conversation",
            "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest", "API_KEY": "sk_1234567890SECRET"}},
            "tool_output": "Authorization: Bearer top-secret-token\nAPI_KEY=sk_1234567890SECRET",
            "success": False,
        }
        self.assertEqual(run_script("post_tool.py", payload, cwd=self.cwd).returncode, 0)
        persisted = "\n".join(path.read_text() for path in (session / "evidence.jsonl", session / "failures.jsonl"))
        self.assertNotIn("top-secret-token", persisted)
        self.assertNotIn("sk_1234567890SECRET", persisted)
        self.assertIn("[REDACTED]", persisted)

    def test_stop_gate_waits_when_antigravity_is_not_idle(self):
        self.init({"mode": "implement", "objective": "x"})
        decision = json.loads(run_script("stop_gate.py", {"fullyIdle": False}, cwd=self.cwd).stdout)
        self.assertEqual(decision["decision"], "continue")

    def test_state_and_stop_gate_require_external_evidence(self):
        session = self.init({
            "mode": "implement", "objective": "x",
            "acceptance_criteria": [{"id": "AC1", "statement": "AC1", "validators": ["unit"]}],
            "validators": [{"id": "unit", "command": [sys.executable, "-c", "pass"], "criterion_ids": ["AC1"]}],
        })
        result = run_script("validator_runner.py", None, "--session-dir", str(session), "--validator-id", "unit", "--criterion-id", "AC1", "--", sys.executable, "-c", "pass", cwd=self.cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        with (session / "evidence.jsonl").open("a") as ledger:
            ledger.write(json.dumps({"source": "read", "file": "src/x.py"}) + "\n")
        self.assertEqual(run_script("post_invocation.py", {}, cwd=self.cwd).returncode, 0)
        state = json.loads((session / "state.json").read_text())
        self.assertEqual(state["pending_criteria"], [])
        self.assertEqual(state["read_files"], ["src/x.py"])
        decision = json.loads(run_script("stop_gate.py", {}, cwd=self.cwd).stdout)
        self.assertEqual(decision["decision"], "allow")

    def test_post_invocation_builds_impact_targets(self):
        session = self.init({"mode": "implement", "objective": "x"})
        (self.cwd / "module.py").write_text("VALUE = 1\n")
        (self.cwd / "consumer.py").write_text("from module import VALUE\n")
        (self.cwd / "test_module.py").write_text("from module import VALUE\n")
        (session / "evidence.jsonl").write_text(json.dumps({"source": "write", "file": "module.py"}) + "\n")
        self.assertEqual(run_script("post_invocation.py", {}, cwd=self.cwd).returncode, 0)
        state = json.loads((session / "state.json").read_text())
        self.assertEqual(state["impact_graph"]["module.py"]["callers"], ["consumer.py"])
        self.assertEqual(state["verification_targets"], ["test_module.py"])

    def test_resume_session_emits_compact_state(self):
        session = self.init({"mode": "implement", "objective": "resume", "acceptance_criteria": ["AC1"]})
        state = json.loads((session / "state.json").read_text())
        state.update({"phase": "verify", "read_files": ["src/x.py"], "next_action": "run tests"})
        (session / "state.json").write_text(json.dumps(state))
        result = run_script("resume_session.py", None, "--session-dir", str(session), cwd=self.cwd)
        context = json.loads(result.stdout)
        self.assertEqual(context["phase"], "verify")
        self.assertEqual(context["next_action"], "run tests")

    def test_failed_required_validator_blocks_stop(self):
        session = self.init({
            "mode": "implement", "objective": "x", "acceptance_criteria": ["AC1"],
            "required_validators": ["pytest"],
        })
        (session / "evidence.jsonl").write_text(
            json.dumps({"criterion": "AC1", "source": "validator", "verdict": "PASS"}) + "\n" +
            json.dumps({"source": "test_run", "command": "pytest", "success": False}) + "\n"
        )
        decision = json.loads(run_script("stop_gate.py", {}, cwd=self.cwd).stdout)
        self.assertEqual(decision["decision"], "continue")
        self.assertIn("acceptance criteria", decision["reason"])

    def test_stop_gate_never_fails_open_after_three_cycles(self):
        self.init({"mode": "implement", "objective": "x", "acceptance_criteria": ["AC1"]})
        decisions = [
            json.loads(run_script("stop_gate.py", {"fullyIdle": True}, cwd=self.cwd).stdout)["decision"]
            for _ in range(4)
        ]
        self.assertEqual(decisions, ["continue"] * 4)


if __name__ == "__main__":
    unittest.main()
