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

    def test_newline_separates_commands(self):
        for command, expected in (("ls\nrm -rf build", "destructive"),
                                  ("git status\r\nrm -rf build", "destructive"),
                                  ("ls\ncp a b", "mutation"),
                                  ("ls\npwd", "none")):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], expected, command)

    def test_rg_pre_and_process_substitution_execute_code(self):
        for command in ("rg --pre ./hook foo", "rg --pre=./hook foo", "cat <(rm -rf x)",
                        "diff <(ls a) <(ls b)"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "mutation", command)

    def test_rg_plain_stays_none(self):
        self.assertEqual(classify_shell("rg -n foo src")["mutation"], "none")

    def test_redirections_without_surrounding_whitespace(self):
        for command in ("echo hi>out.txt", "echo hi>>out.txt", "ls 2>err.txt",
                        "echo hi> out.txt", "echo hi>> out.txt", "echo hi >out.txt",
                        "echo hi >>out.txt", "cat<in.txt", "cat< in.txt",
                        "cat <in.txt", ">out.txt", ">>out.txt", "2>err.txt",
                        ">file", ">>file", "2>file", "> file"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "mutation", command)

    def test_redirect_without_whitespace_paths_extracted(self):
        self.assertEqual(classify_shell("echo hi>out.txt")["paths"], ["out.txt"])
        self.assertEqual(classify_shell("echo hi>>out.txt")["paths"], ["out.txt"])
        self.assertEqual(classify_shell("ls 2>err.txt")["paths"], ["err.txt"])
        self.assertEqual(classify_shell("cat<in.txt")["paths"], ["in.txt"])

    def test_dangerous_leading_env_vars_classified_mutation(self):
        for command in (
            "LD_PRELOAD=/tmp/x.so ls",
            "LD_LIBRARY_PATH=/tmp/evil ls",
            "DYLD_INSERT_LIBRARIES=/tmp/x.dylib ls",
            "GIT_PAGER=./evil git log",
            "PAGER=./evil git log",
            "GIT_EXTERNAL_DIFF=./evil git diff",
            "GIT_EDITOR=./evil git status",
            "PYTHONPATH=/tmp/evil python3 --version",
            "NODE_OPTIONS='--require /evil.js' node --version",
            "BASH_ENV=/tmp/evil bash --version",
            "env LD_PRELOAD=/tmp/x.so ls",
            "sudo GIT_PAGER=./evil git log",
            "env -i PAGER=./evil git log",
        ):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "mutation", command)

    def test_inert_leading_env_vars_remain_read_only(self):
        for command in (
            "VAR=1 ls",
            "DEBUG=1 git status",
            "LANG=C git status",
            "LC_ALL=C git diff",
            "FOO=bar echo hello",
        ):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "none", command)
    def test_wrapper_commands_with_flags_preserve_severity(self):
        for command in (
            "sudo -n rm x",
            "nice -n5 rm x",
            "nice -n 5 rm x",
            "nice -5 rm x",
            "sudo -u root rm x",
            "sudo -u root -g wheel rm x",
            "sudo -E rm x",
            "sudo -- rm x",
            "stdbuf -oL rm x",
            "stdbuf -i0 -o0 -e0 rm x",
            "time -p rm x",
            "command -p rm x",
            "sudo -n nice -n5 rm x",
            "sudo -n git reset --hard",
        ):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "destructive", command)

    def test_wrapper_commands_with_flags_read_only(self):
        for command in (
            "sudo -n ls",
            "nice -n5 ls",
            "nice -n 10 git diff",
            "sudo -u root ls",
            "sudo -E ls",
            "stdbuf -oL ls",
            "time -p ls",
            "command -p ls",
            "sudo -- ls",
            "sudo -n git status",
        ):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "none", command)

    def test_wrapper_unknown_flag_fails_closed_to_destructive(self):
        for command in (
            "sudo --unknown-flag rm x",
            "sudo --unknown-flag ls",
            "nice --unknown-flag ls",
            "stdbuf --unknown-flag ls",
            "time --unknown-flag ls",
        ):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "destructive", command)

    def test_git_read_only_subcommands_with_write_or_exec_flags(self):
        for command in ("git diff --output=out.patch", "git show --output out.txt HEAD",
                        "git log --output=o", "git diff --ext-diff",
                        "git -c diff.external=./hook diff", "git -c core.pager=./x log",
                        "git -c include.path=/tmp/evil log", "git -c core.askpass=/tmp/evil log",
                        "git -c includeIf.gitdir:/foo.path=/tmp/evil diff",
                        "git -C sub -c core.pager=./x log",
                        "git --git-dir /tmp/x -c core.pager=./p log",
                        "git --work-tree /tmp/w -c core.pager=./p log",
                        "git --git-dir=/tmp/x -c core.pager=./p log",
                        "git --work-tree=/tmp/w -c core.pager=./p log",
                        "git -C /tmp/a -C /tmp/b -c diff.external=./hook diff",
                        "git branch newbranch", "git branch feat HEAD~1",
                        "git branch -u origin/main", "git branch --set-upstream-to=origin/main"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "mutation", command)

    def test_git_branch_force_is_destructive(self):
        for command in ("git branch -f main HEAD~5", "git branch --force main HEAD~5"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "destructive", command)

    def test_git_read_only_forms_stay_none(self):
        for command in ("git branch", "git branch -a", "git branch -vv", "git branch --show-current",
                        "git branch --list 'feat*'", "git branch --merged main",
                        "git branch --contains HEAD", "git diff --stat", "git -c color.ui=never diff",
                        "git -C sub -c color.ui=never log", "git --git-dir /tmp/x -c color.ui=never status",
                        "git --work-tree /tmp/w -c color.ui=never diff",
                        "git log --oneline -5", "git -C sub status"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "none", command)

    def test_rsync_is_destructive(self):
        self.assertEqual(classify_shell("rsync -a src/ dst/")["mutation"], "destructive")

    def test_sed_write_and_exec_scripts_are_mutation(self):
        for command in ("sed -n 'w out.txt' f", "sed 's/a/b/w out' f", "sed '1e rm x' f",
                        "sed -e 's/a/b/W out' f", "sed 's/x/id/e' f", "sed -n '1,5w out' f",
                        "sed -n '/err/w errors.txt' f", "sed -f prog.sed f",
                        "sed -n -e 'p' -e 'w out' f"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "mutation", command)

    def test_sed_inplace_variants_are_mutation(self):
        for command in ("sed --in-place=.bak s/a/b/ f",
                        "sed --in-place s/a/b/ f",
                        "sed -ni s/a/b/ f",
                        "sed -i.bak s/a/b/ f",
                        "sed -in s/a/b/ f",
                        "sed -Ei s/a/b/ f",
                        "sed -ri s/a/b/ f"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "mutation", command)

    def test_sed_filter_scripts_stay_none(self):
        for command in ("sed s/a/b/ f", "sed -n p f", "sed -e 's/a/b/g' -e '/x/d' f",
                        "sed '1,5d' f", "sed -n '/err/p' f", "sed -l 70 's/a/b/' f",
                        "sed -e 's/a/b/' -e p f", "sed -n '$p' f"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "none", command)

    def test_operand_extraction(self):
        result = classify_shell("cat a | tee out1 out2")
        self.assertIn("out1", result["paths"])
        self.assertIn("out2", result["paths"])
        dd = classify_shell("dd if=/dev/zero of=disk.img bs=1M")
        self.assertIn("disk.img", dd["paths"])
        sed = classify_shell("sed -i s/a/b/ a.py")
        self.assertEqual(sed["paths"], ["a.py"])
        sed_multi = classify_shell("sed -i.bak -e s/a/b/ a.py b.py")
        self.assertEqual(sed_multi["paths"], ["a.py", "b.py"])
        sed_read = classify_shell("sed s/a/b/ a.py")
        self.assertEqual(sed_read["paths"], [])

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
            try:
                os.symlink(str(base / "outside.txt"), str(base / "work" / "evil"))
            except OSError as error:
                if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                    self.skipTest("symlink creation requires Windows developer mode or privilege")
                raise
            self.assertFalse(target_in_scope("work/evil", ["work"], [base]))

    def test_legitimate_nested_path_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertTrue(target_in_scope("work/a/b.py", ["work"], [base]))


class ConfineTests(unittest.TestCase):
    def test_cwd_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = os.getcwd()
            try:
                os.chdir(tmp)
                for bad in ("..", "../..", "/etc", "/tmp"):
                    with self.subTest(cwd=bad):
                        self.assertRaises(ValueError, confine_cwd, bad)
            finally:
                os.chdir(original)

    def test_subdir_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp) / "pkg"
            sub.mkdir()
            original = os.getcwd()
            try:
                os.chdir(tmp)
                self.assertEqual(confine_cwd("pkg"), sub.resolve())
            finally:
                os.chdir(original)

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
