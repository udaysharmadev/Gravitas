"""V5 round-2 regressions: decide borderlines, failure recovery, skill refs."""
import json
import os
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
from stop_gate import resolution_deficits


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

    def resolve_failure(self, *args):
        env = os.environ.copy()
        isolated_home = str(self.cwd / ".test-user-home")
        env["HOME"] = isolated_home
        if os.name == "nt":
            env["USERPROFILE"] = isolated_home
        return subprocess.run(
            [sys.executable, str(ROOT / "gravitas_cli.py"), "resolve-failure", *args],
            text=True, capture_output=True, cwd=ROOT, env=env, check=False)

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
        with (session / "failures.jsonl").open("a") as handle:
            handle.write(json.dumps({
                "fingerprint": fp, "resolved": True, "resolution_id": "forged",
                "reason": "invented resolution", "timestamp": "2026-01-01T00:00:00+00:00",
                "required_reads": ["new.txt"], "criterion_ids": [],
            }) + "\n")
        still_denied = self.pre_tool({"tool_name": "write_to_file",
                                      "tool_input": {"TargetFile": "new.txt"}})
        self.assertEqual(still_denied["decision"], "deny")

        result = self.resolve_failure(
             "--session-dir", str(session), "--fingerprint", fp,
             "--reason", "transient outage over", "--file", "new.txt")
        self.assertEqual(result.returncode, 0, result.stderr)
        resolution = json.loads(result.stdout)
        self.assertTrue(resolution["ok"])
        self.assertEqual(resolution["required_reads"], ["new.txt"])
        self.assertTrue(resolution["resolution_id"])
        failure_records = [
            json.loads(line) for line in (session / "failures.jsonl").read_text().splitlines()
        ]
        latest_marker = dict(failure_records[-1])
        failure_records[-1]["reason"] = "tampered resolution"
        (session / "failures.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in failure_records))
        tampered = self.pre_tool({"tool_name": "write_to_file",
                                  "tool_input": {"TargetFile": "new.txt"}})
        self.assertEqual(tampered["decision"], "deny")
        failure_records[-1] = latest_marker
        (session / "failures.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in failure_records))
        allowed = self.pre_tool({"tool_name": "write_to_file",
                                 "tool_input": {"TargetFile": "new.txt"}})
        self.assertEqual(allowed["decision"], "allow")
        with (session / "failures.jsonl").open("a") as handle:
            handle.write(json.dumps({
                "tool": "write_to_file", "fingerprint": fp, "cause": "retry failed"
            }) + "\n")
        reblocked = self.pre_tool({"tool_name": "write_to_file",
                                   "tool_input": {"TargetFile": "new.txt"}})
        self.assertEqual(reblocked["decision"], "deny")
        failures = [
            json.loads(line) for line in (session / "failures.jsonl").read_text().splitlines()
        ]
        evidence = [
            json.loads(line) for line in (session / "evidence.jsonl").read_text().splitlines()
        ]
        self.assertEqual(resolution_deficits(failures, evidence, {}), [])

    def test_resolved_failure_blocks_completion_until_reread_and_fresh_pass(self):
        command = [sys.executable, "-c", "pass"]
        session = self.init({
            "mode": "implement",
            "objective": "x",
            "allowed_write_scope": ["."],
            "acceptance_criteria": [
                {"id": "AC1", "statement": "the change works", "validators": ["unit"]}
            ],
            "validators": [
                {"id": "unit", "command": command, "criterion_ids": ["AC1"]}
            ],
        })
        target = self.cwd / "src" / "target.py"
        target.parent.mkdir()
        target.write_text("value = 1\n")

        from gravitas_policy import action_fingerprint
        command_text = subprocess.list2cmdline(command)
        fingerprint = action_fingerprint("run_command", {"CommandLine": command_text})
        (session / "failures.jsonl").write_text(json.dumps({
            "tool": "run_command",
            "input_summary": {"CommandLine": command_text},
            "fingerprint": fingerprint,
            "error": "transient failure",
        }) + "\n")
        initial = test_runtime.run_script(
            "validator_runner.py", None, "--session-dir", str(session),
            "--validator-id", "unit", "--criterion-id", "AC1",
            "--", *command, cwd=self.cwd,
        )
        self.assertEqual(initial.returncode, 0, initial.stderr)

        resolved = self.resolve_failure(
             "--session-dir", str(session), "--fingerprint", fingerprint,
             "--reason", "transient cause is gone",
             "--file", "src/target.py")
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertEqual(json.loads(resolved.stdout)["required_reads"], ["src/target.py"])
        self.assertEqual(json.loads(resolved.stdout)["criterion_ids"], ["AC1"])
        from jsonschema import Draft7Validator
        schema = json.loads((ROOT / "schemas/evidence.schema.json").read_text())
        resolution_record = json.loads((session / "evidence.jsonl").read_text().splitlines()[-1])
        Draft7Validator(schema).validate(resolution_record)

        def gate():
            return json.loads(test_runtime.run_script(
                "stop_gate.py", {}, cwd=self.cwd).stdout)

        failures_path = session / "failures.jsonl"
        failure_records = [json.loads(line) for line in failures_path.read_text().splitlines()]
        original_marker = dict(failure_records[-1])
        failure_records[-1]["required_reads"] = ["src/other.py"]
        failures_path.write_text(
            "".join(json.dumps(record) + "\n" for record in failure_records))
        tampered = gate()
        self.assertEqual(tampered["decision"], "continue")
        self.assertIn("resolution metadata is not anchored", tampered["reason"])
        failure_records[-1] = original_marker
        failures_path.write_text(
            "".join(json.dumps(record) + "\n" for record in failure_records))

        blocked = gate()
        self.assertEqual(blocked["decision"], "continue", blocked)
        self.assertIn("re-read src/target.py", blocked["reason"])

        reread = test_runtime.run_script(
            "post_tool.py",
            {"toolCall": {"name": "view_file", "args": {"AbsolutePath": str(target)}}},
            cwd=self.cwd,
        )
        self.assertEqual(reread.returncode, 0, reread.stderr)
        blocked = gate()
        self.assertEqual(blocked["decision"], "continue")
        self.assertIn("fresh validator PASS for AC1", blocked["reason"])

        fresh = test_runtime.run_script(
            "validator_runner.py", None, "--session-dir", str(session),
            "--validator-id", "unit", "--criterion-id", "AC1",
            "--", *command, cwd=self.cwd,
        )
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        self.assertEqual(gate()["decision"], "allow")

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
