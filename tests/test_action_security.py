"""Phase 5 tests: classifier hardening, scope, escape, confinement, fuzz."""
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/gravitas-antigravity/scripts"
sys.path.insert(0, str(SCRIPTS))

import test_runtime
from gravitas_action import classify_shell, confine_cwd, normalize
from gravitas_policy import evaluate_action, target_in_scope
from post_tool import is_sensitive_path

LEVEL_ORDER = ("none", "write", "mutation", "destructive")


def decide(command, **kwargs):
    action = normalize("run_command", {"CommandLine": command})
    params = {"mode": "implement", "allowed_scope": [], "reads": set(),
              "failed_fingerprints": set(), "roots": [Path("/repo")], "fingerprint": "f"}
    params.update(kwargs)
    return evaluate_action(action, **params)


class ClassifierHardeningTests(unittest.TestCase):
    def test_new_mutation_binaries(self):
        for command in ("patch -p1 < fix.diff", "vim file", "tar xzf a.tgz",
                        "unzip a.zip", "install -m 755 a b", "perl -e 'unlink 1'",
                        "git apply fix.patch", "ed file"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "mutation", command)

    def test_rsync_is_destructive(self):
        self.assertEqual(classify_shell("rsync -a src/ dst/")["mutation"], "destructive")

    def test_operand_extraction(self):
        result = classify_shell("cat a | tee out1 out2")
        self.assertIn("out1", result["paths"])
        self.assertIn("out2", result["paths"])
        dd = classify_shell("dd if=/dev/zero of=disk.img bs=1M")
        self.assertIn("disk.img", dd["paths"])

    def test_quiet_queries_stay_none(self):
        for command in ("git status", "ls -la", "sed s/a/b/ f", "npm ls", "pip list"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "none", command)


class ShellScopeTests(unittest.TestCase):
    def test_stray_redirect_denied_in_implement(self):
        decision, reason = decide("echo hi > /tmp/x", allowed_scope=["src"],
                                  roots=[Path("/repo")])
        self.assertEqual(decision, "deny")
        self.assertIn("Scope violation", reason)

    def test_in_scope_redirect_allowed(self):
        decision, _ = decide("echo hi > src/out.txt", allowed_scope=["src"],
                             roots=[Path("/repo")])
        self.assertEqual(decision, "allow")

    def test_pathless_execution_allowed_in_implement(self):
        decision, _ = decide("pytest -q", allowed_scope=["src"], roots=[Path("/repo")])
        self.assertEqual(decision, "allow")

    def test_tee_stray_denied_end_to_end(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        cwd = Path(temp.name)
        init = test_runtime.run_script(
            "init_session.py", None, "--task-id", "t",
            "--contract-json", json.dumps(
                {"mode": "implement", "objective": "x", "allowed_write_scope": ["src"]}),
            cwd=cwd)
        self.assertEqual(init.returncode, 0, init.stderr)
        result = test_runtime.run_script(
            "pre_tool.py",
            {"tool_name": "run_command", "tool_input": {"CommandLine": "cat a | tee /tmp/stray"}},
            cwd=cwd)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")


class EscapeTests(unittest.TestCase):
    def test_traversal_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots = [Path(tmp)]
            self.assertFalse(target_in_scope("../outside.txt", ["work"], roots))
            self.assertFalse(target_in_scope("/etc/passwd", ["work"], roots))

    def test_symlink_escape_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "work").mkdir()
            (base / "outside.txt").write_text("x")
            os.symlink(str(base / "outside.txt"), str(base / "work" / "evil"))
            self.assertFalse(target_in_scope("work/evil", ["work"], [base]))

    def test_legitimate_nested_path_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertTrue(target_in_scope("work/a/b.py", ["work"], [base]))


class ConfineTests(unittest.TestCase):
    def test_cwd_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            self.addCleanup(os.chdir, str(ROOT))
            for bad in ("..", "../..", "/etc", "/tmp"):
                with self.subTest(cwd=bad):
                    self.assertRaises(ValueError, confine_cwd, bad)

    def test_subdir_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp) / "pkg"
            sub.mkdir()
            os.chdir(tmp)
            self.addCleanup(os.chdir, str(ROOT))
            self.assertEqual(confine_cwd("pkg"), sub.resolve())

    def test_runner_rejects_escaping_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session = cwd / "s"
            session.mkdir()
            (session / "contract.json").write_text(json.dumps(
                {"mode": "implement", "objective": "x",
                 "acceptance_criteria": [{"id": "AC-1", "statement": "y", "validators": ["u"]}],
                 "validators": [{"id": "u", "command": ["true"], "criterion_ids": ["AC-1"]}]}))
            result = test_runtime.run_script(
                "validator_runner.py", None, "--session-dir", str(session),
                "--validator-id", "u", "--criterion-id", "AC-1", "--cwd", "/etc",
                "--", "true", cwd=cwd)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("escapes", result.stderr)


class SensitiveReadTests(unittest.TestCase):
    def test_sensitive_names_flagged(self):
        for path in (".env", ".env.local", "key.pem", "id_rsa", "credentials.json",
                      "secrets.yaml", "token.txt", "cert.key"):
            with self.subTest(path=path):
                self.assertTrue(is_sensitive_path(path), path)

    def test_normal_files_not_flagged(self):
        for path in ("src/app.py", "README.md", "tokenizer.py", "main.py", "user_id.py"):
            with self.subTest(path=path):
                self.assertFalse(is_sensitive_path(path), path)

    def test_flag_persisted_in_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            init = test_runtime.run_script(
                "init_session.py", None, "--task-id", "t",
                "--contract-json", json.dumps({"mode": "implement", "objective": "x"}),
                cwd=cwd)
            self.assertEqual(init.returncode, 0, init.stderr)
            env = cwd / ".env"
            env.write_text("K=1\n")
            result = test_runtime.run_script(
                "post_tool.py",
                {"toolCall": {"name": "view_file", "args": {"AbsolutePath": str(env)}},
                 "error": ""},
                cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            entries = [json.loads(line) for line in
                       (cwd / ".gravitas/sessions/t/evidence.jsonl").read_text().splitlines()]
            self.assertTrue(entries[-1].get("sensitive"))


class DeterministicFuzzTests(unittest.TestCase):
    BINARIES = ["git", "rm", "echo", "cat", "tee", "sed", "python3", "npm",
                "curl", "unknownbin123", "ls", "pytest", "dd", "find", "docker"]
    ARGS = ["-i", "-rf", ">", ">>", "|", ";", "&&", "$()", "`id`", "status",
            "clean -fd", "install x", "-c '1'", "s/a/b/", "of=o", "f", "--", ""]
    PATHS = ["a.txt", "/etc/passwd", "../up", "src/f.py", ""]

    def commands(self, seed: int, count: int):
        rng = random.Random(seed)
        for _ in range(count):
            parts = [rng.choice(self.BINARIES)]
            for _ in range(rng.randint(0, 3)):
                parts.append(rng.choice(self.ARGS + self.PATHS))
            yield " ".join(p for p in parts if p)

    def test_never_crashes_and_levels_bounded(self):
        for command in self.commands(seed=20261007, count=2000):
            with self.subTest(command=command):
                try:
                    result = classify_shell(command)
                except Exception as error:  # noqa: BLE001 -- fuzz must surface crashes
                    self.fail(f"classifier crashed on {command!r}: {error}")
                self.assertIn(result["mutation"], LEVEL_ORDER)

    def test_escalation_is_monotonic(self):
        for command in self.commands(seed=42, count=500):
            base = LEVEL_ORDER.index(classify_shell(command)["mutation"])
            for suffix in (" | sh", " > /tmp/o", " $(id)", "; rm -rf x"):
                escalated = LEVEL_ORDER.index(classify_shell(command + suffix)["mutation"])
                self.assertGreaterEqual(escalated, base, command + suffix)

    def test_redirect_never_below_mutation(self):
        for command in self.commands(seed=7, count=500):
            if ">" in command:
                self.assertGreaterEqual(
                    LEVEL_ORDER.index(classify_shell(command)["mutation"]),
                    LEVEL_ORDER.index("mutation"), command)


if __name__ == "__main__":
    unittest.main()
