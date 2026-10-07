"""Context Engine tests: repo graph, retrieval, elision, summaries."""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/gravitas-antigravity/scripts"
sys.path.insert(0, str(SCRIPTS))

import test_runtime
from gravitas_context import elide_output, summarize_session
from gravitas_repo import context_for, get_index, rank_related

MODULE = "def connect(dsn):\n    return dsn\n"
CONSUMER = "from module import connect\nconnect('x')\n"
TEST_MODULE = "from module import connect\ndef test_c():\n    assert connect('x') == 'x'\n"
UNRELATED = "def other():\n    return 1\n"


def make_repo():
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    (root / "module.py").write_text(MODULE)
    (root / "consumer.py").write_text(CONSUMER)
    (root / "test_module.py").write_text(TEST_MODULE)
    (root / "unrelated.py").write_text(UNRELATED)
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    return temp, root


class RepoGraphTests(unittest.TestCase):
    def test_symbols_imports_and_edges(self):
        temp, root = make_repo()
        self.addCleanup(temp.cleanup)
        index = get_index(root, refresh=False)
        module = index["files"]["module.py"]
        self.assertIn("connect", module["symbols"])
        self.assertIn("consumer.py", module["imported_by"])
        self.assertIn("test_module.py", module["imported_by"])
        self.assertIn("consumer.py", module["callers"])
        self.assertIn("test_module.py", module["tested_by"])
        self.assertNotIn("unrelated.py", module["callers"])
        self.assertEqual(module["configured_by"], ["pyproject.toml"])

    def test_ranked_reasons(self):
        temp, root = make_repo()
        self.addCleanup(temp.cleanup)
        ranked = {entry["path"]: entry for entry in rank_related(get_index(root, refresh=False), "module.py")}
        self.assertIn("imports-target", ranked["consumer.py"]["reasons"])
        self.assertIn("covers-target", ranked["test_module.py"]["reasons"])
        self.assertGreater(ranked["consumer.py"]["score"], 0)
        # same-directory is a weak signal: unrelated ranks below real relations
        self.assertLess(ranked["unrelated.py"]["score"], ranked["consumer.py"]["score"])

    def test_progressive_disclosure_grows(self):
        temp, root = make_repo()
        self.addCleanup(temp.cleanup)
        index = get_index(root, refresh=False)
        target = context_for(index, ["module.py"], "target")
        dependency = context_for(index, ["module.py"], "dependency")
        subsystem = context_for(index, ["module.py"], "subsystem")
        self.assertEqual(target["files"], ["module.py"])
        self.assertIn("consumer.py", dependency["files"])
        self.assertIn("test_module.py", dependency["files"])
        self.assertTrue(set(dependency["files"]) <= set(subsystem["files"]))
        self.assertLessEqual(len(subsystem["files"]), 60)

    def test_index_cache_refreshes_on_change(self):
        temp, root = make_repo()
        self.addCleanup(temp.cleanup)
        index = get_index(root, refresh=False)
        self.assertNotIn("added.py", index["files"])
        (root / "added.py").write_text("def fresh():\n    return 2\n")
        refreshed = get_index(root, refresh=True)
        self.assertIn("added.py", refreshed["files"])
        self.assertIn("fresh", refreshed["files"]["added.py"]["symbols"])

    def test_co_changed_from_git_history(self):
        if shutil.which("git") is None:
            self.skipTest("git not available")
        temp, root = make_repo()
        self.addCleanup(temp.cleanup)
        env = {"GIT_CONFIG_NOSYSTEM": "1", "HOME": str(root)}
        subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=env)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True, env=env)
        subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True, env=env)
        subprocess.run(["git", "add", "module.py", "consumer.py"], cwd=root, check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "one"], cwd=root, check=True, env=env)
        subprocess.run(["git", "add", "module.py", "consumer.py"], cwd=root, check=True, env=env)
        subprocess.run(["git", "commit", "--allow-empty", "-qm", "two"], cwd=root, check=True, env=env)
        index = get_index(root, refresh=False)
        self.assertIn("consumer.py", index["files"]["module.py"]["co_changed"])


class ElisionTests(unittest.TestCase):
    def test_short_text_untouched(self):
        result = elide_output("a\nb\n", budget_lines=60)
        self.assertFalse(result["elided"])
        self.assertEqual(result["text"], "a\nb\n")

    def test_elision_keeps_errors_and_reports_drop(self):
        lines = [f"line {i}" for i in range(200)]
        lines[100] = "FAILED tests/test_x.py::test_y - assert 1 == 2"
        lines[150] = "Error: something broke"
        result = elide_output("\n".join(lines), budget_lines=60)
        self.assertTrue(result["elided"])
        self.assertIn("FAILED tests/test_x.py::test_y", result["text"])
        self.assertIn("Error: something broke", result["text"])
        self.assertIn("elided", result["text"])
        self.assertGreater(result["dropped_lines"], 100)

    def test_digest_stable(self):
        text = "\n".join(f"line {i}" for i in range(100))
        self.assertEqual(elide_output(text)["sha256"], elide_output(text)["sha256"])


class SummaryTests(unittest.TestCase):
    def init(self, cwd, contract):
        result = test_runtime.run_script(
            "init_session.py", None, "--task-id", "t",
            "--contract-json", json.dumps(contract), cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        return cwd / ".gravitas/sessions/t"

    def test_summary_preserves_identifiers(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        cwd = Path(temp.name)
        session = self.init(cwd, {
            "mode": "implement", "objective": "fix login redirect",
            "acceptance_criteria": [{"id": "AC-login", "statement": "login redirects to /home"}],
            "allowed_write_scope": ["src/auth/"],
        })
        (session / "state.json").write_text(json.dumps({
            "phase": "verify", "read_files": ["src/auth/login.py"],
            "files_touched": ["src/auth/login.py"],
            "decisions": [{"action": "patch login", "reason": "redirect target wrong"}],
            "next_action": "run pytest src/auth/ -q",
        }))
        (session / "coverage.json").write_text(json.dumps({"AC-login": "PASS"}))
        (session / "failures.jsonl").write_text(json.dumps({
            "tool": "run_command", "fingerprint": "abc123",
            "error": "pytest exit 1: src/auth/login.py:42 AssertionError"}) + "\n")
        summary = summarize_session(session)
        self.assertEqual(summary["objective"], "fix login redirect")
        self.assertEqual(summary["acceptance_criteria"]["AC-login"]["status"], "PASS")
        self.assertEqual(summary["acceptance_criteria"]["AC-login"]["statement"],
                          "login redirects to /home")
        self.assertEqual(summary["allowed_scope"], ["src/auth/"])
        self.assertEqual(summary["next_action"], "run pytest src/auth/ -q")
        self.assertEqual(len(summary["failed_approaches"]), 1)
        self.assertIn("src/auth/login.py:42", summary["failed_approaches"][0]["cause"])

    def test_resume_includes_summary(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        cwd = Path(temp.name)
        session = self.init(cwd, {"mode": "implement", "objective": "x"})
        result = test_runtime.run_script(
            "resume_session.py", None, "--session-dir", str(session), cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)
        self.assertEqual(context["summary"]["objective"], "x")
        self.assertIn("acceptance_criteria", context["summary"])
        self.assertIn("failed_approaches", context["summary"])

    def test_summarize_cli(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        cwd = Path(temp.name)
        session = self.init(cwd, {"mode": "implement", "objective": "cli-check"})
        result = subprocess.run(
            [sys.executable, str(ROOT / "gravitas_cli.py"), "summarize",
             "--session-dir", str(session)],
            text=True, capture_output=True, cwd=cwd, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["objective"], "cli-check")

    def test_context_cli(self):
        temp, root = make_repo()
        self.addCleanup(temp.cleanup)
        result = subprocess.run(
            [sys.executable, str(ROOT / "gravitas_cli.py"), "context",
             "--root", str(root), "--changed", "module.py", "--depth", "dependency"],
            text=True, capture_output=True, cwd=root, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)
        self.assertIn("consumer.py", context["files"])
        self.assertIn("imports-target", context["reasons"]["consumer.py"])


if __name__ == "__main__":
    unittest.main()
