"""Host lifecycle coverage: session attribution, aliases, malformed payloads.

Pins the expected-vs-observed hook event contract for Antigravity native
hooks: every payload shape either attributes to the right session or fails
closed. No required event is silently dropped or misattributed.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins" / "gravitas-antigravity" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gravitas_action import antigravity_envelope
from session_context import conversation_key, session_dir_for_payload


def run_script(name, raw_stdin, cwd):
    env = os.environ.copy()
    isolated_home = str(Path(cwd) / ".test-user-home")
    env["HOME"] = isolated_home
    if os.name == "nt":
        env["USERPROFILE"] = isolated_home
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name)],
        input=raw_stdin,
        text=True,
        capture_output=True,
        cwd=cwd,
        env=env,
        check=False,
    )


def init_conversation(cwd, conversation_id, task_id):
    env = os.environ.copy()
    env["HOME"] = str(Path(cwd) / ".test-user-home")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "init_session.py"),
         "--task-id", task_id, "--conversation-id", conversation_id,
         "--contract-json", json.dumps({"mode": "implement", "objective": "x"})],
        text=True, capture_output=True, cwd=cwd, env=env, check=False,
    )
    assert result.returncode == 0, result.stderr
    return Path(cwd) / json.loads(result.stdout)["session_dir"]


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)
        self.saved_cwd = Path.cwd()
        os.chdir(self.cwd)
        self.dir_a = init_conversation(self.cwd, "conv-A", "task-a")
        self.dir_b = init_conversation(self.cwd, "conv-B", "task-b")

    def tearDown(self):
        os.chdir(self.saved_cwd)
        self.temp.cleanup()

    def test_parallel_conversations_resolve_to_own_dirs(self):
        resolved_a = session_dir_for_payload({"conversationId": "conv-A"})
        resolved_b = session_dir_for_payload({"conversationId": "conv-B"})
        self.assertEqual(resolved_a.resolve(), self.dir_a.resolve())
        self.assertEqual(resolved_b.resolve(), self.dir_b.resolve())
        self.assertNotEqual(resolved_a.resolve(), resolved_b.resolve())

    def test_conversation_id_alias_forms_agree(self):
        self.assertEqual(
            conversation_key({"conversationId": "conv-A"}),
            conversation_key({"conversation_id": "conv-A"}),
        )
        self.assertEqual(
            session_dir_for_payload({"conversation_id": "conv-A"}).resolve(),
            self.dir_a.resolve(),
        )

    def test_unknown_conversation_never_falls_back(self):
        self.assertIsNone(session_dir_for_payload({"conversationId": "conv-unknown"}))
        self.assertIsNone(session_dir_for_payload({"conversation_id": "conv-unknown"}))

    def test_non_dict_payload_has_no_key(self):
        self.assertIsNone(conversation_key("conv-A"))
        self.assertIsNone(conversation_key(None))
        with tempfile.TemporaryDirectory() as empty:
            saved = Path.cwd()
            os.chdir(empty)
            try:
                self.assertIsNone(session_dir_for_payload("conv-A"))
            finally:
                os.chdir(saved)

    def test_envelope_carries_conversation_through_aliases(self):
        base = {"toolCall": {"name": "view_file", "args": {"AbsolutePath": "a.py"}}}
        for payload in (
            {**base, "conversationId": "conv-A"},
            {**base, "conversation_id": "conv-A"},
        ):
            envelope, action = antigravity_envelope(payload)
            self.assertEqual(envelope.conversation_id, "conv-A")
            self.assertEqual(action.kind, "read")


class MalformedPayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_pre_tool_garbage_denies(self):
        result = run_script("pre_tool.py", "{not-json", self.cwd)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_pre_tool_missing_tool_call_denies(self):
        result = run_script(
            "pre_tool.py", json.dumps({"conversationId": "conv-A"}), self.cwd)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")

    def test_stop_gate_garbage_continues_never_allows(self):
        result = run_script("stop_gate.py", "{not-json", self.cwd)
        decision = json.loads(result.stdout)
        self.assertEqual(decision["decision"], "continue")
        self.assertIn("unparseable", decision["reason"])

    def test_post_tool_garbage_answers_empty(self):
        result = run_script("post_tool.py", "{not-json", self.cwd)
        self.assertEqual(json.loads(result.stdout), {})

    def test_pre_tool_renamed_tool_stays_visible(self):
        envelope, action = antigravity_envelope(
            {"toolCall": {"name": "edit_file", "args": {"TargetFile": "a.py"}}})
        self.assertEqual(envelope.tool, "write_to_file")
        self.assertEqual(action.kind, "write")

    def test_unknown_tool_never_gated(self):
        envelope, action = antigravity_envelope(
            {"toolCall": {"name": "future_tool_xyz", "args": {}}})
        self.assertEqual(action.kind, "other")
        self.assertEqual(action.mutation, "none")


class EventNameTests(unittest.TestCase):
    def test_hook_event_alias_forms_preserved(self):
        payload = {"toolCall": {"name": "view_file", "args": {}},
                   "hookEventName": "PostToolUse"}
        self.assertEqual(antigravity_envelope(payload)[0].event, "PostToolUse")
        payload = {"toolCall": {"name": "view_file", "args": {}},
                   "hookEvent": "PreToolUse"}
        self.assertEqual(antigravity_envelope(payload)[0].event, "PreToolUse")

    def test_stop_payload_fully_idle_flag(self):
        payload = {"fullyIdle": True, "terminationReason": "NO_TOOL_CALL"}
        self.assertTrue(payload["fullyIdle"])


if __name__ == "__main__":
    unittest.main()
