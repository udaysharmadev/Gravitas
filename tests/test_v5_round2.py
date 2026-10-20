"""V5 round-2 regressions: decide borderlines, failure recovery, skill refs."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/gravitas-antigravity/scripts"
sys.path.insert(0, str(SCRIPTS))

import test_runtime
from gravitas_policy import decide


class DecideBorderlineTests(unittest.TestCase):
    def test_high_stakes_overrides_trivial(self):
        for signals in ({"trivial": True, "destructive": True},
                        {"trivial": True, "migration": True},
                        {"read_only": True, "security": True}):
            with self.subTest(signals=signals):
                self.assertEqual(decide(signals)["planning"], "deep", signals)

    def test_plain_trivial_stays_direct(self):
        self.assertEqual(decide({"trivial": True})["planning"], "direct")
        self.assertEqual(decide({"read_only": True})["planning"], "direct")

    def test_garbage_counts_do_not_crash(self):
        for signals in ({"files": "abc"}, {"repeated_failures": "x", "files": None},
                        {"independent_workstreams": "many"}, {"files": -3}):
            with self.subTest(signals=signals):
                record = decide(signals)
                self.assertIn(record["planning"], ("direct", "compact", "deep", "replan"))


class FailureRecoveryTests(unittest.TestCase):
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

    def pre_tool(self, payload):
        return json.loads(test_runtime.run_script("pre_tool.py", payload, cwd=self.cwd).stdout)

    def test_resolved_failure_rearms_exact_action(self):
        session = self.init({"mode": "implement", "objective": "x",
                             "allowed_write_scope": ["."]})
        from gravitas_policy import action_fingerprint
        fp = action_fingerprint("write_to_file", {"TargetFile": "new.txt"})
        (session / "failures.jsonl").write_text(json.dumps({
            "tool": "write_to_file", "fingerprint": fp, "cause": "flaky env"}) + "\n")
        denied = self.pre_tool({"tool_name": "write_to_file",
                                "tool_input": {"TargetFile": "new.txt"}})
        self.assertEqual(denied["decision"], "deny")
        result = subprocess.run(
            [sys.executable, str(ROOT / "gravitas_cli.py"), "resolve-failure",
             "--session-dir", str(session), "--fingerprint", fp,
             "--reason", "transient outage over"],
            text=True, capture_output=True, cwd=ROOT, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])
        allowed = self.pre_tool({"tool_name": "write_to_file",
                                 "tool_input": {"TargetFile": "new.txt"}})
        self.assertEqual(allowed["decision"], "allow")

    def test_unresolved_failure_still_bans(self):
        session = self.init({"mode": "implement", "objective": "x",
                             "allowed_write_scope": ["."]})
        from gravitas_policy import action_fingerprint
        fp = action_fingerprint("write_to_file", {"TargetFile": "other.txt"})
        (session / "failures.jsonl").write_text(json.dumps({
            "tool": "write_to_file", "fingerprint": fp, "cause": "real bug"}) + "\n")
        denied = self.pre_tool({"tool_name": "write_to_file",
                                "tool_input": {"TargetFile": "other.txt"}})
        self.assertEqual(denied["decision"], "deny")


class SkillReferenceTests(unittest.TestCase):
    def test_skill_mentioned_refs_exist_and_ship(self):
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib
        text = (ROOT / "skills/gravitas/SKILL.md").read_text()
        refs = sorted(set(re.findall(r"(?:references|resources)/[\w.-]+\.md", text)))
        self.assertTrue(refs, "SKILL.md should link task references")
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
        patterns = [p for g in pyproject["tool"]["setuptools"]["data-files"].values() for p in g]
        shipped = {p.relative_to(ROOT).as_posix() for pat in patterns for p in ROOT.glob(pat)}
        for ref in refs:
            self.assertTrue((ROOT / "skills/gravitas" / ref).is_file(), ref)
            self.assertIn(f"skills/gravitas/{ref}", shipped, f"wheel omits {ref}")


if __name__ == "__main__":
    unittest.main()
