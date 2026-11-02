"""V5 hardening regressions: enforcement fail-closed, classifier, evidence, init, packaging."""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/gravitas-antigravity/scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

import test_runtime
from gravitas_action import classify_shell
from evidence_chain import (
    append_evidence,
    anchor_path,
    backfill_anchors,
    canonical_json,
    sha256,
    verify_with_anchor,
)
from gravitas_init import _copy_tree, init_opencode


def guard(*args):
    result = subprocess.run(
        [sys.executable, str(ROOT / "gravitas_cli.py"), "guard", *args],
        text=True, capture_output=True, cwd=ROOT, check=False)
    return result.returncode, json.loads(result.stdout)


def make_contract(tmp, contract):
    path = Path(tmp) / "contract.json"
    path.write_text(json.dumps(contract))
    return str(path)


class GuardPolicyStateTests(unittest.TestCase):
    def test_missing_contract_denies_mutating_allows_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "nope.json")
            _, write_out = guard("--contract", missing, "--envelope", json.dumps(
                {"tool": "write_to_file", "args": {"TargetFile": "a.txt"},
                 "workspace_roots": [tmp], "host": "opencode"}))
            self.assertEqual(write_out["decision"], "deny")
            self.assertEqual(write_out["policy_state"], "unconfigured")
            _, read_out = guard("--contract", missing, "--envelope", json.dumps(
                {"tool": "view_file", "args": {"AbsolutePath": "a.txt"},
                 "workspace_roots": [tmp], "host": "opencode"}))
            self.assertEqual(read_out["decision"], "allow")
            self.assertIn("warning", read_out)

    def test_corrupt_contract_denies_mutating(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("not-json{{{")
            _, out = guard("--contract", str(bad), "--envelope", json.dumps(
                {"tool": "write_to_file", "args": {"TargetFile": "a.txt"},
                 "workspace_roots": [tmp], "host": "opencode"}))
            self.assertEqual(out["decision"], "deny")
            self.assertEqual(out["policy_state"], "degraded")

    def test_invalid_mode_denies_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            contract = make_contract(tmp, {"mode": "implemnt", "allowed_write_scope": ["."]})
            _, out = guard("--contract", contract, "--envelope", json.dumps(
                {"tool": "edit", "args": {"filePath": "a.py"}, "host": "opencode"}))
            self.assertEqual(out["decision"], "deny")
            self.assertIn("implemnt", out["reason"])

    def test_empty_mutating_args_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            contract = make_contract(tmp, {"mode": "implement", "allowed_write_scope": ["."]})
            _, out = guard("--contract", contract, "--envelope", json.dumps(
                {"tool": "run_command", "args": {}, "workspace_roots": [tmp], "host": "opencode"}))
            self.assertEqual(out["decision"], "deny")

    def test_unknown_tool_allowed_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            contract = make_contract(tmp, {"mode": "implement", "allowed_write_scope": ["."]})
            _, out = guard("--contract", contract, "--envelope", json.dumps(
                {"tool": "frobnicate", "args": {}, "workspace_roots": [tmp], "host": "opencode"}))
            self.assertEqual(out["decision"], "allow")
            self.assertIn("unknown tool", out.get("warning", ""))


class ShimHookTests(unittest.TestCase):
    SHIM = ROOT / "adapters" / "opencode" / "plugin" / "gravitas.js"

    def node(self, script):
        if shutil.which("node") is None:
            self.skipTest("node not available")
        result = subprocess.run(["node", "--input-type=module", "-e", script],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_hook_denies_missing_mutating_args_without_guard(self):
        out = self.node(
            f"import('{self.SHIM.as_uri()}').then(async m => {{"
            "  const hook = (await m.GravitasPlugin({directory: '/tmp'}))['tool.execute.before'];"
            "  try { await hook({tool:'bash',sessionID:'s',callID:'c'}, {args:{}});"
            "    console.log('ALLOWED'); }"
            "  catch (e) { console.log('DENIED:' + e.message.slice(0, 60)); }"
            "});")
        self.assertIn("DENIED", out)

    def test_hook_denies_missing_tool(self):
        out = self.node(
            f"import('{self.SHIM.as_uri()}').then(async m => {{"
            "  const hook = (await m.GravitasPlugin({directory: '/tmp'}))['tool.execute.before'];"
            "  try { await hook({}, {args:{}}); console.log('ALLOWED'); }"
            "  catch (e) { console.log('DENIED'); }"
            "});")
        self.assertEqual(out, "DENIED")

    def test_hook_denies_unreachable_guard(self):
        out = self.node(
            f"import('{self.SHIM.as_uri()}').then(async m => {{"
            "  const hook = (await m.GravitasPlugin({directory: '/nonexistent-xyz'}))['tool.execute.before'];"
            "  try { await hook({tool:'bash',sessionID:'s',callID:'c'}, {args:{command:'ls'}});"
            "    console.log('ALLOWED'); }"
            "  catch (e) { console.log('DENIED'); }"
            "});")
        self.assertEqual(out, "DENIED")

    def test_glob_maps_to_find_by_name(self):
        out = self.node(
            f"import('{self.SHIM.as_uri()}').then(m => console.log("
            "  JSON.stringify(m.toEnvelope('glob', {pattern: '*.py'}, '/tmp'))));")
        self.assertEqual(json.loads(out)["tool"], "find_by_name")


class ClassifierV5Tests(unittest.TestCase):
    CASES = {
        "git branch -D x": "destructive",
        "git branch -d x": "destructive",
        "git branch": "none",
        "git branch --list": "none",
        "git stash drop": "destructive",
        "git stash clear": "destructive",
        "git stash list": "none",
        "git worktree remove /tmp/w --force": "destructive",
        "git worktree list": "none",
        "git -C /other/path status": "none",
        "find . -execdir rm {} +": "destructive",
        "find . -ok rm {} +": "destructive",
        "python3 -": "mutation",
        "python3 --version": "none",
        "python3": "mutation",
        "VAR=1 rm -rf x": "destructive",
        "env VAR=1 rm x": "destructive",
        "sudo rm -rf /tmp/x": "destructive",
        'sh -c "rm -rf /tmp/x"': "destructive",
        "echo x | xargs rm -rf": "destructive",
    }

    def test_v5_corpus(self):
        for command, expected in self.CASES.items():
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], expected, command)

    def test_git_dir_operand_visible_to_scope(self):
        self.assertIn("/etc", classify_shell("git -C /etc status")["paths"])


class EvidenceV5Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)

    def init(self, contract):
        result = test_runtime.run_script(
            "init_session.py", None, "--task-id", "t",
            "--contract-json", json.dumps(contract), cwd=self.cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.cwd / ".gravitas" / "sessions" / "t"

    def test_stale_completed_not_retained(self):
        from post_invocation import update_state_from_evidence
        session = self.init({"mode": "implement", "objective": "x",
                             "acceptance_criteria": [{"id": "AC-1", "statement": "y"}]})
        ledger = session / "evidence.jsonl"
        ledger.write_text(
            json.dumps({"source": "validator", "validator_id": "u", "criterion_ids": ["AC-1"],
                        "command": ["true"], "exit_code": 0, "verdict": "PASS",
                        "event_hash": "h1",
                        "timestamp": "2026-01-01T00:00:00+00:00"}) + "\n"
            + json.dumps({"source": "write", "file": "a.py",
                          "timestamp": "2026-06-01T00:00:00+00:00"}) + "\n")
        (session / "contract.json").write_text(json.dumps(
            {"mode": "implement", "objective": "x",
             "acceptance_criteria": [{"id": "AC-1", "statement": "y"}]}))
        state = {"completed_criteria": ["AC-1"], "files_touched": [], "read_files": []}
        updated = update_state_from_evidence(state, session)
        self.assertNotIn("AC-1", updated["completed_criteria"])
        self.assertIn("AC-1", updated["pending_criteria"])

    def test_tampered_chain_blocks_gate(self):
        command = [sys.executable, "-c", "pass"]
        session = self.init({"mode": "implement", "objective": "x",
                             "acceptance_criteria": [{"id": "AC1", "statement": "y"}],
                             "validators": [{"id": "u", "command": command,
                                             "criterion_ids": ["AC1"]}]})
        run = test_runtime.run_script(
            "validator_runner.py", None, "--session-dir", str(session),
            "--validator-id", "u", "--criterion-id", "AC1",
            "--", *command, cwd=self.cwd)
        self.assertEqual(run.returncode, 0, run.stderr)
        ledger = session / "evidence.jsonl"
        ledger.write_text(ledger.read_text().replace('"exit_code":0', '"exit_code":1'))
        gate = json.loads(test_runtime.run_script("stop_gate.py", {}, cwd=self.cwd).stdout)
        self.assertEqual(gate["decision"], "continue")
        self.assertIn("chain", gate["reason"])

    def test_user_anchor_detects_rewritten_chain_and_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / ".gravitas" / "sessions" / "task"
            home = root / "private-home"
            session.mkdir(parents=True)
            with patch.dict(
                os.environ, {"HOME": str(home), "USERPROFILE": str(home)}
            ):
                first = append_evidence(session, {"source": "read", "file": "a.py"})
                second = append_evidence(session, {"source": "read", "file": "b.py"})
                ledger = session / "evidence.jsonl"
                original = ledger.read_text(encoding="utf-8")
                self.assertEqual(verify_with_anchor(session), (True, "chain valid; ledger head anchored"))

                forged = {
                    "source": "validator", "timestamp": "2026-10-19T00:00:00+00:00",
                    "previous_event_hash": None,
                }
                forged["event_hash"] = sha256(forged)
                ledger.write_text(canonical_json(forged) + "\n", encoding="utf-8")
                self.assertFalse(verify_with_anchor(session)[0])

                ledger.write_text(original, encoding="utf-8")
                anchors = anchor_path(session)
                anchor_lines = anchors.read_text(encoding="utf-8").splitlines()
                anchors.write_text(anchor_lines[0] + "\n", encoding="utf-8")
                valid, reason = verify_with_anchor(session)
                self.assertFalse(valid)
                self.assertIn("not anchored", reason)
                self.assertNotEqual(first["event_hash"], second["event_hash"])

    def test_stop_gate_rejects_self_consistent_unanchored_rewrite(self):
        command = [sys.executable, "-c", "pass"]
        session = self.init({"mode": "implement", "objective": "x",
                             "acceptance_criteria": [{"id": "AC1", "statement": "y"}],
                             "validators": [{"id": "u", "command": command,
                                             "criterion_ids": ["AC1"]}]})
        run = test_runtime.run_script(
            "validator_runner.py", None, "--session-dir", str(session),
            "--validator-id", "u", "--criterion-id", "AC1",
            "--", *command, cwd=self.cwd)
        self.assertEqual(run.returncode, 0, run.stderr)
        forged = {
            "source": "validator", "validator_id": "u", "criterion_ids": ["AC1"],
            "command": command, "command_sha256": sha256(command), "exit_code": 0,
            "verdict": "PASS", "timestamp": "2026-10-19T00:00:00+00:00",
            "previous_event_hash": None,
        }
        forged["event_hash"] = sha256(forged)
        (session / "evidence.jsonl").write_text(canonical_json(forged) + "\n")
        gate = json.loads(test_runtime.run_script("stop_gate.py", {}, cwd=self.cwd).stdout)
        self.assertEqual(gate["decision"], "continue")
        self.assertIn("anchor", gate["reason"])

    def test_validator_timeout_records_fail(self):
        command = [sys.executable, "-c", "import time; time.sleep(30)"]
        session = self.init({"mode": "implement", "objective": "x",
                             "validators": [{"id": "u", "command": command}]})
        run = test_runtime.run_script(
            "validator_runner.py", None, "--session-dir", str(session),
            "--validator-id", "u", "--timeout", "1",
            "--", *command, cwd=self.cwd)
        self.assertNotEqual(run.returncode, 0)
        out = json.loads(run.stdout)
        self.assertTrue(out.get("timed_out"))
        self.assertEqual(out.get("verdict"), "FAIL")


class EvidenceAnchorFailureTests(unittest.TestCase):
    """Blockers A/B/C: anchor-store failures stay fail-closed without crashing."""

    def test_broken_anchor_store_marks_pending_and_blocks_gate(self):
        # Blocker B(1): the anchor directory path is blocked by a file, so
        # anchoring fails, but the ledger append still succeeds, flagged.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / ".gravitas" / "sessions" / "task"
            home = root / "private-home"
            session.mkdir(parents=True)
            blocked = home / ".gravitas" / "anchors"
            blocked.parent.mkdir(parents=True)
            blocked.write_text("not a directory", encoding="utf-8")
            with patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}):
                record = append_evidence(session, {"source": "read", "file": "a.py"})
                self.assertTrue(record.get("anchor_pending"))
                self.assertIn("anchor_error", record)
                # The ledger entry itself is durable and schema-valid.
                ledger = [json.loads(line)
                          for line in (session / "evidence.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertEqual(len(ledger), 1)
                self.assertTrue(ledger[0].get("anchor_pending"))
                from jsonschema import Draft7Validator
                schema = json.loads((ROOT / "schemas/evidence.schema.json").read_text())
                Draft7Validator(schema).validate(ledger[0])
                # Blocker B(2): verification reports a deficit, not a crash.
                valid, reason = verify_with_anchor(session)
                self.assertFalse(valid)
                self.assertIn("anchor pending", reason)

    def test_corrupt_anchor_file_marks_pending_without_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / ".gravitas" / "sessions" / "task"
            home = root / "private-home"
            session.mkdir(parents=True)
            with patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}):
                first = append_evidence(session, {"source": "read", "file": "a.py"})
                self.assertNotIn("anchor_pending", first)
                anchor_path(session).write_text("garbage{{{not json\n", encoding="utf-8")
                second = append_evidence(session, {"source": "read", "file": "b.py"})
                self.assertTrue(second.get("anchor_pending"))
                # A corrupt anchor chain stays fail-closed (deficit, no traceback).
                self.assertFalse(verify_with_anchor(session)[0])

    def test_post_tool_survives_broken_anchor_store(self):
        # Hook contract: stdout {} and RC 0 even when anchoring fails.
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            blocked = cwd / ".test-user-home" / ".gravitas" / "anchors"
            blocked.parent.mkdir(parents=True)
            blocked.write_text("not a directory", encoding="utf-8")
            result = test_runtime.run_script(
                "post_tool.py",
                {"toolCall": {"name": "view_file",
                              "args": {"AbsolutePath": str(cwd / "m.py")}}},
                cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {})

    def test_resolve_failure_writes_no_marker_when_ledger_append_fails(self):
        # Blocker A: ledger-first ordering leaves no orphan marker behind.
        import gravitas_cli
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session"
            session.mkdir()
            (session / "failures.jsonl").write_text(json.dumps({
                "tool": "write_to_file",
                "input_summary": {"TargetFile": "new.txt"},
                "fingerprint": "fp-orphan",
                "cause": "flaky env",
            }) + "\n", encoding="utf-8")
            before = (session / "failures.jsonl").read_text(encoding="utf-8")
            args = argparse.Namespace(session_dir=str(session), fingerprint="fp-orphan",
                                      reason="cause gone", file=[], criterion_id=[])
            with patch("evidence_chain.append_evidence", side_effect=OSError("disk full")):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    rc = gravitas_cli.cmd_resolve_failure(args)
            self.assertEqual(rc, 1)
            self.assertIn("could not be anchored", buffer.getvalue())
            self.assertEqual((session / "failures.jsonl").read_text(encoding="utf-8"), before)
            self.assertFalse((session / "evidence.jsonl").exists())

    def test_backfill_anchors_legacy_ledger(self):
        # Blocker C: pre-anchor ledger -> actionable deficit -> backfill -> verify passes.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / ".gravitas" / "sessions" / "legacy"
            home = root / "private-home"
            session.mkdir(parents=True)
            previous = None
            for name in ("a.py", "b.py"):
                entry = {"source": "read", "file": name,
                         "timestamp": "2026-01-01T00:00:00+00:00",
                         "previous_event_hash": previous}
                entry["event_hash"] = sha256(dict(entry))
                with (session / "evidence.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(canonical_json(entry) + "\n")
                previous = entry["event_hash"]
            env = os.environ.copy()
            env["HOME"] = str(home)
            if os.name == "nt":
                env["USERPROFILE"] = str(home)
            with patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}):
                valid, reason = verify_with_anchor(session)
                self.assertFalse(valid)
                self.assertIn("backfill", reason)
                ok, detail = backfill_anchors(session)
                self.assertTrue(ok, detail)
                self.assertEqual(verify_with_anchor(session),
                                 (True, "chain valid; ledger head anchored"))
                self.assertTrue(backfill_anchors(session)[0])
            # The CLI surfaces the same upgrade path.
            legacy2 = root / ".gravitas" / "sessions" / "legacy2"
            legacy2.mkdir(parents=True)
            shutil.copy(session / "evidence.jsonl", legacy2 / "evidence.jsonl")
            bare = subprocess.run(
                [sys.executable, str(ROOT / "gravitas_cli.py"), "verify",
                 "--session-dir", str(legacy2)],
                text=True, capture_output=True, cwd=ROOT, env=env, check=False)
            self.assertNotEqual(bare.returncode, 0)
            self.assertIn("backfill", json.loads(bare.stdout)["reason"])
            filled = subprocess.run(
                [sys.executable, str(ROOT / "gravitas_cli.py"), "verify",
                 "--session-dir", str(legacy2), "--backfill-anchors"],
                text=True, capture_output=True, cwd=ROOT, env=env, check=False)
            self.assertEqual(filled.returncode, 0, filled.stderr)
            self.assertTrue(json.loads(filled.stdout)["valid"])


class InitV5Tests(unittest.TestCase):
    def test_bad_profile_leaves_no_partial_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = init_opencode(Path(tmp), profile="nonexistent", source_root=ROOT)
            self.assertFalse(result["ok"])
            self.assertEqual(result["installed"], [])
            self.assertFalse((Path(tmp) / ".agents").exists())
            self.assertFalse((Path(tmp) / ".opencode").exists())

    def test_copy_tree_missing_source_is_noop(self):
        installed, skipped = [], []
        _copy_tree(Path("/nonexistent-xyz"), Path(tempfile.gettempdir()) / "gravitas-noop", installed, skipped)
        self.assertEqual((installed, skipped), ([], []))


class PackagingV5Tests(unittest.TestCase):
    def test_wheel_manifest_ships_all_skills_and_rules(self):
        text = (ROOT / "pyproject.toml").read_text()
        for needle in ("gravitas-highstakes", "SESSION_FAILURES", "rules"):
            self.assertIn(needle, text)

    def test_doctor_reports_hardened_checks(self):
        result = subprocess.run([sys.executable, str(ROOT / "gravitas_cli.py"), "doctor"],
                                text=True, capture_output=True, cwd=ROOT, check=False)
        self.assertEqual(result.returncode, 0, result.stdout)
        checks = json.loads(result.stdout)
        for key in ("highstakes_skill", "post_tool_hook", "post_invocation_hook",
                    "adapter_permissions"):
            self.assertIn(key, checks)
        self.assertTrue(checks["highstakes_skill"])


if __name__ == "__main__":
    unittest.main()
