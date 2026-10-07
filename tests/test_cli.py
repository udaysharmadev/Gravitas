"""Phase 8 CLI tests: init auto-detect, explain, migrate, update, doctor."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

sys.path.insert(0, str(ROOT))
from gravitas_init import detect_hosts


def cli(*args, cwd=ROOT):
    result = subprocess.run(
        [sys.executable, str(ROOT / "gravitas_cli.py"), *args],
        text=True, capture_output=True, cwd=cwd, check=False)
    return result


class DetectHostsTests(unittest.TestCase):
    def test_opencode_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "opencode.json").write_text("{}")
            self.assertEqual(detect_hosts(Path(tmp)), ["opencode"])

    def test_antigravity_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".agents").mkdir()
            self.assertEqual(detect_hosts(Path(tmp)), ["antigravity"])

    def test_no_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_hosts(Path(tmp)), [])


class InitAutoTests(unittest.TestCase):
    def test_auto_installs_detected_host_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".opencode").mkdir()
            result = cli("init", "--root", tmp, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(output["hosts"], ["opencode"])
            self.assertTrue((Path(tmp) / ".agents" / "skills" / "gravitas" / "SKILL.md").is_file())
            self.assertTrue((Path(tmp) / ".opencode" / "plugins" / "gravitas.js").is_file())

    def test_explicit_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = cli("init", "--host", "antigravity", "--root", tmp, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((Path(tmp) / ".opencode").exists())


class ExplainTests(unittest.TestCase):
    def make_session(self, root):
        base = Path(root) / ".gravitas" / "sessions" / "s1"
        base.mkdir(parents=True)
        (base / "contract.json").write_text(json.dumps({
            "mode": "implement", "objective": "fix login",
            "acceptance_criteria": [{"id": "AC-1", "statement": "login works"}],
            "allowed_write_scope": ["src/"]}))
        (base / "state.json").write_text(json.dumps(
            {"phase": "verify", "next_action": "run tests"}))
        (base / "coverage.json").write_text(json.dumps({"AC-1": "PENDING"}))
        (base / "evidence.jsonl").write_text("")
        (base / "failures.jsonl").write_text("")
        return base

    def test_explain_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = self.make_session(tmp)
            result = cli("explain", "--session-dir", str(session), cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("fix login", result.stdout)
            self.assertIn("[PENDING] AC-1", result.stdout)
            self.assertIn("Evidence deficit", result.stdout)

    def test_explain_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = self.make_session(tmp)
            result = cli("explain", "--session-dir", str(session), "--json", cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["objective"], "fix login")
            self.assertTrue(data["deficit"])

    def test_explain_missing_dir(self):
        result = cli("explain", "--session-dir", "/nope/nothing", cwd=ROOT)
        self.assertNotEqual(result.returncode, 0)


class MigrateTests(unittest.TestCase):
    def test_mode_aliases_migrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / ".gravitas" / "sessions" / "old"
            base.mkdir(parents=True)
            (base / "contract.json").write_text(json.dumps(
                {"mode": "plan-only", "objective": "x",
                 "acceptance_criteria": [{"id": "AC-1", "statement": "y"}]}))
            result = cli("migrate", "--root", tmp, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(len(output["migrated"]), 1)
            contract = json.loads((base / "contract.json").read_text())
            self.assertEqual(contract["mode"], "plan")

    def test_issues_reported_not_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / ".gravitas" / "sessions" / "odd"
            base.mkdir(parents=True)
            (base / "contract.json").write_text(json.dumps({"mode": "yolo"}))
            result = cli("migrate", "--root", tmp, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertTrue(output["issues"])


class UpdateTests(unittest.TestCase):
    def test_update_without_check(self):
        result = cli("update", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("installed", json.loads(result.stdout))


class DoctorTests(unittest.TestCase):
    def test_doctor_reports_adapter_and_project_keys(self):
        result = cli("doctor", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout)
        checks = json.loads(result.stdout)
        for key in ("adapters", "project_opencode_contract", "project_opencode_skill"):
            self.assertIn(key, checks)
        self.assertTrue(checks["adapters"])


if __name__ == "__main__":
    unittest.main()
