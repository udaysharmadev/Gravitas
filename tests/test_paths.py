"""Path identity matrix (issue #71): canonicalize at record, fold at compare.

Contract under test:

- ``canonical_path`` is the record-time identity: absolute, joined onto the
  first workspace root when relative, and realpath-resolved (``.``, ``..``
  and symlinks). Case and Unicode form are preserved, so a stored path
  still names the file the host touched.
- ``path_key`` is the compare-time identity. It folds case only when the
  volume folds case (probed, see ``case_insensitive_fs``) and folds
  Unicode to NFC only on macOS (APFS/HFS+ are normalization-insensitive;
  ext4 and NTFS are not). Folding on a sensitive volume would make
  ``cafe\\u0301/`` or ``SRC/`` look like an in-scope ``café/`` or ``src/``
  while the write lands elsewhere -- a scope bypass, not a convenience.
- ``..`` escapes are resolved BEFORE scope comparison and stay denied
  under every folding combination.

Platform expectations:

- macOS (default APFS): case-insensitive and normalization-insensitive;
  ``File.py`` satisfies a read of ``file.py`` and NFD satisfies NFC. A
  case-sensitive APFS volume is detected by the probe and not folded.
- Windows: ``\\`` and ``/`` are both separators and NTFS is
  case-insensitive. On POSIX ``\\`` is a legal filename character, so it
  is folded only under Windows semantics (``windows=True`` here).
- Linux: nothing is folded beyond realpath resolution.

TOCTOU boundary: canonicalization happens when the hook runs. A symlink
swapped or a directory renamed between the policy decision and the host's
actual write is outside what a pre-action hook can observe; this is the
same documented limit as enumerable shell writes in gravitas_policy.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/gravitas-antigravity/scripts"
sys.path.insert(0, str(SCRIPTS))

import test_runtime
from gravitas_action import canonical_path, case_insensitive_fs, normalize, path_key
from gravitas_policy import evaluate_action, target_in_scope

NFC = unicodedata.normalize("NFC", "café")
NFD = unicodedata.normalize("NFD", "café")


def symlink_or_skip(test, source, link):
    try:
        os.symlink(str(source), str(link))
    except OSError as error:
        if os.name == "nt" and getattr(error, "winerror", None) == 1314:
            test.skipTest("symlink creation requires Windows developer mode or privilege")
        raise


def write_decision(target, reads, roots):
    action = normalize("write_to_file", {"TargetFile": target})
    decision, _ = evaluate_action(action, mode="implement", allowed_scope=[], reads=set(reads),
                                  failed_fingerprints=set(), roots=roots, fingerprint="f")
    return decision


class CanonicalPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.real = self.base.resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_relative_dot_and_absolute_variants_agree(self):
        expected = self.real / "src" / "a.py"
        for raw in ("src/a.py", "./src/a.py", "src/./a.py", "src/x/../a.py",
                    str(self.base / "src" / "a.py")):
            with self.subTest(raw=raw):
                self.assertEqual(canonical_path(raw, [self.base]), expected)

    def test_symlink_resolves_to_target(self):
        (self.base / "real").mkdir()
        symlink_or_skip(self, self.base / "real", self.base / "link")
        self.assertEqual(canonical_path("link/a.py", [self.base]), self.real / "real" / "a.py")

    def test_dotdot_escape_is_visible_after_canonicalization(self):
        self.assertEqual(canonical_path("work/../../x", [self.base]), self.real.parent / "x")

    def test_case_and_unicode_are_preserved_at_record(self):
        self.assertEqual(canonical_path("File.py", [self.base]).name, "File.py")
        self.assertEqual(canonical_path(NFD, [self.base]).name, NFD)

    def test_windows_separators_fold_under_windows_semantics(self):
        self.assertEqual(canonical_path("src\\a.py", [self.base], windows=True),
                         self.real / "src" / "a.py")
        self.assertEqual(canonical_path("work\\..\\..\\x", [self.base], windows=True),
                         self.real.parent / "x")

    @unittest.skipIf(os.name == "nt", "backslash is a separator on Windows")
    def test_backslash_is_a_filename_character_on_posix(self):
        self.assertEqual(canonical_path("src\\a.py", [self.base]).name, "src\\a.py")


class PathKeyTests(unittest.TestCase):
    def test_case_folds_only_when_volume_folds(self):
        upper, lower = Path("/r/File.py"), Path("/r/file.py")
        self.assertEqual(path_key(upper, case_insensitive=True), path_key(lower, case_insensitive=True))
        self.assertNotEqual(path_key(upper, case_insensitive=False), path_key(lower, case_insensitive=False))

    def test_unicode_folds_only_when_volume_folds(self):
        nfc, nfd = Path("/r") / NFC, Path("/r") / NFD
        self.assertEqual(path_key(nfc, case_insensitive=False, unicode_insensitive=True),
                         path_key(nfd, case_insensitive=False, unicode_insensitive=True))
        self.assertNotEqual(path_key(nfc, case_insensitive=False, unicode_insensitive=False),
                            path_key(nfd, case_insensitive=False, unicode_insensitive=False))

    def test_probe_matches_the_real_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            (base / "Probe.txt").write_text("x")
            folds = (base / "probe.txt").exists()
            self.assertEqual(case_insensitive_fs(base / "Probe.txt"), folds)


class ScopeMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        (self.base / "src").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_relative_dot_and_absolute_targets_in_scope(self):
        for target in ("src/a.py", "./src/a.py", str(self.base / "src" / "a.py"),
                       str(self.base.resolve() / "src" / "a.py")):
            with self.subTest(target=target):
                self.assertTrue(target_in_scope(target, ["src"], [self.base]))

    def test_case_variant_scoped_by_volume_semantics(self):
        self.assertTrue(target_in_scope("SRC/a.py", ["src"], [self.base], case_insensitive=True))
        self.assertTrue(target_in_scope("src/a.py", ["Src"], [self.base], case_insensitive=True))
        self.assertFalse(target_in_scope("SRC/a.py", ["src"], [self.base], case_insensitive=False))

    def test_case_sensitive_scope_requires_exact_components(self):
        self.assertTrue(target_in_scope("src/a.py", ["src"], [self.base], case_insensitive=False))
        self.assertFalse(target_in_scope("SRC/a.py", ["src"], [self.base], case_insensitive=False))
        self.assertFalse(target_in_scope("src/a.py", ["SRC"], [self.base], case_insensitive=False))

    def test_scope_comparison_uses_path_components_not_string_prefixes(self):
        self.assertFalse(target_in_scope("source/a.py", ["src"], [self.base], case_insensitive=False))
        self.assertTrue(target_in_scope("src/nested/a.py", ["src"], [self.base], case_insensitive=False))

    def test_case_sensitive_scope_checks_each_workspace_root(self):
        with tempfile.TemporaryDirectory() as directory:
            second_root = Path(directory)
            (second_root / "src").mkdir()
            roots = [self.base, second_root]
            self.assertTrue(target_in_scope("src/a.py", ["src"], roots, case_insensitive=False))
            self.assertFalse(target_in_scope("SRC/a.py", ["src"], roots, case_insensitive=False))

    def test_dotdot_escape_denied_under_every_fold(self):
        for fold in (True, False):
            for target in ("src/../../x", "SRC/../../x", "../outside.txt", "/etc/passwd"):
                with self.subTest(fold=fold, target=target):
                    self.assertFalse(target_in_scope(target, ["src"], [self.base], case_insensitive=fold))

    def test_symlink_escape_denied(self):
        (self.base / "outside.txt").write_text("x")
        symlink_or_skip(self, self.base / "outside.txt", self.base / "src" / "evil")
        self.assertFalse(target_in_scope("src/evil", ["src"], [self.base], case_insensitive=True))

    @unittest.skipUnless(sys.platform == "darwin", "macOS folds Unicode normalization")
    def test_nfd_target_in_nfc_scope_on_macos(self):
        self.assertTrue(target_in_scope(f"{NFD}/a.py", [NFC], [self.base]))


class ReadBeforeWriteMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        (self.base / "file.py").write_text("x = 1\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_relative_dot_absolute_and_resolved_reads_satisfy_write(self):
        for read in ("file.py", "./file.py", "sub/../file.py", str(self.base / "file.py"),
                     str(self.base.resolve() / "file.py")):
            with self.subTest(read=read):
                self.assertEqual(write_decision("file.py", [read], [self.base]), "allow")

    def test_read_through_symlink_satisfies_write(self):
        symlink_or_skip(self, self.base, self.base.parent / (self.base.name + "-link"))
        link = self.base.parent / (self.base.name + "-link")
        try:
            self.assertEqual(write_decision("file.py", [str(link / "file.py")], [self.base]), "allow")
        finally:
            link.unlink()

    def test_case_variant_read_follows_volume(self):
        folds = case_insensitive_fs(self.base.resolve())
        self.assertEqual(write_decision("file.py", ["File.py"], [self.base]),
                         "allow" if folds else "deny")

    def test_read_of_other_file_does_not_satisfy(self):
        (self.base / "other").mkdir()
        self.assertEqual(write_decision("file.py", ["other/file.py", "../file.py"], [self.base]), "deny")

    @unittest.skipUnless(sys.platform == "darwin", "macOS folds Unicode normalization")
    def test_nfd_read_satisfies_nfc_write_on_macos(self):
        (self.base / NFC).write_text("x")
        self.assertEqual(write_decision(NFC, [NFD], [self.base]), "allow")


class RecordTimeTests(unittest.TestCase):
    """post_tool stores the canonical path; pre_tool compares it by key."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)
        init = test_runtime.run_script(
            "init_session.py", None, "--task-id", "t",
            "--contract-json", json.dumps({"mode": "implement", "objective": "x"}),
            cwd=self.cwd)
        self.assertEqual(init.returncode, 0, init.stderr)
        self.session = self.cwd / json.loads(init.stdout)["session_dir"]
        (self.cwd / "Module.py").write_text("x = 1\n")

    def tearDown(self):
        self.temp.cleanup()

    def record_read(self, path):
        result = test_runtime.run_script(
            "post_tool.py", {"toolCall": {"name": "view_file", "args": {"AbsolutePath": path}}, "error": ""},
            cwd=self.cwd)
        self.assertEqual(result.returncode, 0, result.stderr)

    def pre_write(self, path):
        result = test_runtime.run_script(
            "pre_tool.py", {"tool_name": "write_to_file", "tool_input": {"TargetFile": path}}, cwd=self.cwd)
        return json.loads(result.stdout)["decision"]

    def test_post_tool_records_canonical_path(self):
        self.record_read("./sub/../Module.py")
        entries = [json.loads(line) for line in (self.session / "evidence.jsonl").read_text().splitlines()]
        self.assertEqual(entries[-1]["file"], str((self.cwd / "Module.py").resolve()))
        self.assertEqual(entries[-1]["file_sha256"], hashlib.sha256((self.cwd / "Module.py").read_bytes()).hexdigest())

    def test_recorded_read_satisfies_absolute_and_case_variant_writes(self):
        self.record_read("./Module.py")
        self.assertEqual(self.pre_write(str(self.cwd / "Module.py")), "allow")
        # Folding volume: same file, satisfied by the recorded read (denied
        # before #71). Sensitive volume: module.py is a new file, so allowed.
        self.assertEqual(self.pre_write("module.py"), "allow")

    def test_dotdot_read_does_not_satisfy_sibling_write(self):
        self.record_read("../Module.py")
        self.assertEqual(self.pre_write("Module.py"), "deny")

    def test_changed_file_after_read_requires_reread(self):
        self.record_read("Module.py")
        (self.cwd / "Module.py").write_text("x = 2\n")
        self.assertEqual(self.pre_write("Module.py"), "deny")

    def test_legacy_path_only_read_requires_reread(self):
        (self.session / "evidence.jsonl").write_text(json.dumps({
            "source": "read", "file": str(self.cwd / "Module.py"),
        }) + "\n")
        self.assertEqual(self.pre_write("Module.py"), "deny")


class OpenCodeGuardTests(unittest.TestCase):
    """The shim forwards raw paths; the guard canonicalizes before policy."""

    def guard(self, cwd, file_path):
        contract = cwd / "contract.json"
        contract.write_text(json.dumps({"mode": "implement", "allowed_write_scope": ["src"]}))
        result = subprocess.run(
            [sys.executable, str(ROOT / "gravitas_cli.py"), "guard", "--contract", str(contract),
             "--envelope", json.dumps({"tool": "edit", "args": {"filePath": file_path},
                                        "workspace_roots": [str(cwd)], "host": "opencode"})],
            text=True, capture_output=True, cwd=cwd, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["decision"]

    def test_guard_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "src").mkdir()
            folds = case_insensitive_fs(cwd.resolve())
            cases = {
                "src/new.py": "allow",
                "./src/new.py": "allow",
                str(cwd.resolve() / "src" / "new.py"): "allow",
                "SRC/new.py": "allow" if folds else "deny",
                "src/../../x.py": "deny",
                "../src/new.py": "deny",
            }
            for file_path, expected in cases.items():
                with self.subTest(file_path=file_path):
                    self.assertEqual(self.guard(cwd, file_path), expected)


if __name__ == "__main__":
    unittest.main()
