"""Regression coverage for the plugin bundle manifest.

The manifest is the bundle's drift detector: CI rebuilds the bundle and
asserts `git diff --exit-code -- dist/gravitas-antigravity` is clean. That
check only means something if the manifest is reproducible on every
operating system, so these tests pin the two properties that guarantee it
(LF-normalized digests, POSIX path ordering) and assert the tracked
manifest still describes the tracked bundle.

The ordering fixture covers both places where POSIX path ordering and
`Path` object ordering disagree: uppercase sorts before lowercase, and
`-` (0x2D) sorts before `/` (0x2F), which places `gravitas-highstakes/`
ahead of `gravitas/`.
"""
import hashlib
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANIFEST_SCRIPT = ROOT / "scripts" / "bundle_manifest.py"
BUNDLE = ROOT / "dist" / "gravitas-antigravity"

# Canonical sources copied into the bundle, as (source dir, bundle dir).
CANONICAL_ROOTS = (
    ("plugins/gravitas-antigravity/scripts", "scripts"),
    ("plugins/gravitas-antigravity/agents", "agents"),
    ("plugins/gravitas-antigravity/rules", "rules"),
    ("skills/gravitas", "skills/gravitas"),
    ("skills/gravitas-highstakes", "skills/gravitas-highstakes"),
)

# Canonical sources copied into the bundle as single files, as
# (source path, bundle path).
CANONICAL_FILES = (
    ("plugins/gravitas-antigravity/plugin.json", "plugin.json"),
    ("plugins/gravitas-antigravity/hooks.json", "hooks.json"),
)


def load_manifest_module():
    spec = importlib.util.spec_from_file_location("bundle_manifest", MANIFEST_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bundle_manifest = load_manifest_module()


def find_bash():
    """Locate a bash able to run the bundle build script, if one exists."""
    found = shutil.which("bash")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ):
        if os.path.exists(candidate):
            return candidate
    return None


BASH = find_bash()

# Interpreter stubs used to drive the build script's failure path. Each one
# records its arguments so the test can prove the version probe was reached.
STUB_UNUSABLE = b"""#!/bin/sh
echo "$*" >> "$GRAVITAS_TEST_STUB_LOG"
echo "stub: no interpreter available" >&2
exit 1
"""

STUB_TOO_OLD = b"""#!/bin/sh
echo "$*" >> "$GRAVITAS_TEST_STUB_LOG"
case "$*" in
  *version_info*) echo "2.7"; exit 1 ;;
esac
exit 0
"""

# Enough of a PATH for the build script to locate itself, without providing
# any interpreter.
STUB_DIRNAME = b"""#!/bin/sh
case "$1" in
  */*) echo "${1%/*}" ;;
  *) echo "." ;;
esac
"""


class ManifestGeneratorTests(unittest.TestCase):
    def test_crlf_and_lf_content_hash_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            lf = base / "lf.txt"
            crlf = base / "crlf.txt"
            lf.write_bytes(b"alpha\nbeta\n")
            crlf.write_bytes(b"alpha\r\nbeta\r\n")
            self.assertEqual(
                bundle_manifest.normalized_digest(lf),
                bundle_manifest.normalized_digest(crlf),
            )

    def test_all_common_newline_forms_hash_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            lf = base / "lf.txt"
            crlf = base / "crlf.txt"
            cr = base / "cr.txt"
            lf.write_bytes(b"alpha\nbeta\n")
            crlf.write_bytes(b"alpha\r\nbeta\r\n")
            cr.write_bytes(b"alpha\rbeta\r")
            digests = {
                bundle_manifest.normalized_digest(lf),
                bundle_manifest.normalized_digest(crlf),
                bundle_manifest.normalized_digest(cr),
            }
            self.assertEqual(len(digests), 1, digests)
            self.assertEqual(
                digests.pop(),
                hashlib.sha256(b"alpha\nbeta\n").hexdigest(),
            )

    def test_mixed_newline_forms_hash_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            mixed = base / "mixed.txt"
            lf = base / "lf.txt"
            mixed.write_bytes(b"alpha\r\nbeta\rgamma\n")
            lf.write_bytes(b"alpha\nbeta\ngamma\n")
            self.assertEqual(
                bundle_manifest.normalized_digest(mixed),
                bundle_manifest.normalized_digest(lf),
            )

    def test_empty_and_unterminated_files_keep_their_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            empty = base / "empty.txt"
            unterminated = base / "unterminated.txt"
            empty.write_bytes(b"")
            unterminated.write_bytes(b"alpha\nbeta")
            self.assertEqual(
                bundle_manifest.normalized_digest(empty),
                hashlib.sha256(b"").hexdigest(),
            )
            self.assertEqual(
                bundle_manifest.normalized_digest(unterminated),
                hashlib.sha256(b"alpha\nbeta").hexdigest(),
            )

    def test_entries_sort_by_posix_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name in (
                "SKILL.md",
                "PROMPT-TEMPLATE.md",
                "agents/explore.md",
                "agents/coordinator.md",
                "gravitas/SKILL.md",
                "gravitas-highstakes/SKILL.md",
            ):
                target = base / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"x\n")
            paths = [
                entry.split("  ", 1)[1]
                for entry in bundle_manifest.manifest_entries(base)
            ]
            self.assertEqual(
                paths,
                [
                    "PROMPT-TEMPLATE.md",
                    "SKILL.md",
                    "agents/coordinator.md",
                    "agents/explore.md",
                    "gravitas-highstakes/SKILL.md",
                    "gravitas/SKILL.md",
                ],
            )

    def test_manifest_excludes_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.txt").write_bytes(b"a\n")
            (base / "SHA256SUMS").write_bytes(b"stale\n")
            self.assertEqual(len(bundle_manifest.manifest_entries(base)), 1)

    def test_only_the_root_manifest_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.txt").write_bytes(b"a\n")
            nested = base / "subdir" / "SHA256SUMS"
            nested.parent.mkdir(parents=True)
            nested.write_bytes(b"nested\n")
            (base / "SHA256SUMS").write_bytes(b"stale\n")
            entries = {
                entry.split("  ", 1)[1]: entry.split("  ", 1)[0]
                for entry in bundle_manifest.manifest_entries(base)
            }
            self.assertNotIn("SHA256SUMS", entries)
            self.assertIn("subdir/SHA256SUMS", entries)
            self.assertEqual(
                entries["subdir/SHA256SUMS"],
                hashlib.sha256(b"nested\n").hexdigest(),
            )
            self.assertIn("a.txt", entries)

    def test_render_uses_lf_line_endings(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.txt").write_bytes(b"a\n")
            (base / "b.txt").write_bytes(b"b\n")
            rendered = bundle_manifest.render_manifest(base)
            self.assertNotIn("\r", rendered)
            self.assertTrue(rendered.endswith("\n"))

    def test_render_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name in ("z.txt", "a.txt", "M.txt"):
                (base / name).write_bytes(name.encode("utf-8"))
            self.assertEqual(
                bundle_manifest.render_manifest(base),
                bundle_manifest.render_manifest(base),
            )


class TrackedBundleTests(unittest.TestCase):
    def test_tracked_manifest_matches_bundle_contents(self):
        tracked = (BUNDLE / "SHA256SUMS").read_text(encoding="utf-8")
        self.assertEqual(
            bundle_manifest.render_manifest(BUNDLE),
            tracked,
            "dist/gravitas-antigravity/SHA256SUMS is stale; "
            "run scripts/build-native-bundle.sh",
        )

    def test_bundle_files_match_canonical_sources(self):
        expected = {bundle_name for _, bundle_name in CANONICAL_FILES}
        for source_name, bundle_name in CANONICAL_FILES:
            source = ROOT / source_name
            copied = BUNDLE / bundle_name
            self.assertTrue(
                copied.is_file(),
                f"bundle is missing {bundle_name}",
            )
            self.assertEqual(
                source.read_bytes().replace(b"\r\n", b"\n"),
                copied.read_bytes().replace(b"\r\n", b"\n"),
                f"bundle copy is out of sync: {bundle_name}",
            )
        for source_root, bundle_root in CANONICAL_ROOTS:
            source_dir = ROOT / source_root
            for source in source_dir.rglob("*"):
                if not source.is_file() or "__pycache__" in source.parts:
                    continue
                relative = source.relative_to(source_dir)
                expected.add(f"{bundle_root}/{relative.as_posix()}")
                copied = BUNDLE / bundle_root / relative
                self.assertTrue(
                    copied.is_file(),
                    f"bundle is missing {bundle_root}/{relative.as_posix()}",
                )
                self.assertEqual(
                    source.read_bytes().replace(b"\r\n", b"\n"),
                    copied.read_bytes().replace(b"\r\n", b"\n"),
                    f"bundle copy is out of sync: {bundle_root}/{relative.as_posix()}",
                )
        actual = {
            path.relative_to(BUNDLE).as_posix()
            for path in BUNDLE.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS"
        }
        self.assertEqual(
            actual,
            expected,
            "bundle contents do not match the canonical sources",
        )

    def test_interpreter_check_precedes_bundle_deletion(self):
        script = (ROOT / "scripts" / "build-native-bundle.sh").read_text(encoding="utf-8")
        self.assertLess(
            script.index("version_info >= (3, 9)"),
            script.index('rm -rf "$bundle"'),
            "the interpreter check must run before the bundle is deleted",
        )


@unittest.skipUnless(BASH, "bash is required to exercise the bundle build guard")
class BuildGuardTests(unittest.TestCase):
    """The build must fail closed and leave the tracked bundle untouched.

    Each case runs the real build script inside an isolated copy of the
    repository, so a failure can never damage the checkout under test.
    """

    def _sandbox(self, base):
        repo = base / "repo"
        repo.mkdir()
        for rel in ("scripts", "plugins", "skills"):
            shutil.copytree(
                ROOT / rel, repo / rel, ignore=shutil.ignore_patterns("__pycache__")
            )
        shutil.copytree(BUNDLE, repo / "dist" / "gravitas-antigravity")
        return repo

    def _stub_bin(self, base, body):
        stub_dir = base / "bin"
        stub_dir.mkdir()
        for name in ("python3", "python", "py"):
            stub = stub_dir / name
            stub.write_bytes(body)
            stub.chmod(0o755)
        return stub_dir

    def _snapshot(self, repo):
        bundle = repo / "dist" / "gravitas-antigravity"
        return {
            "files": sorted(
                path.relative_to(bundle).as_posix()
                for path in bundle.rglob("*")
                if path.is_file()
            ),
            "manifest": (bundle / "SHA256SUMS").read_bytes(),
        }

    def _run_build(self, repo, path_value, log):
        env = dict(os.environ)
        env["PATH"] = path_value
        env["GRAVITAS_TEST_STUB_LOG"] = str(log)
        return subprocess.run(
            [BASH, "scripts/build-native-bundle.sh"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
        )

    def _assert_bundle_intact(self, repo, before):
        bundle = repo / "dist" / "gravitas-antigravity"
        self.assertTrue(bundle.is_dir(), "the bundle directory was deleted")
        after = sorted(
            path.relative_to(bundle).as_posix()
            for path in bundle.rglob("*")
            if path.is_file()
        )
        self.assertEqual(after, before["files"], "the bundle contents changed")
        self.assertEqual(
            (bundle / "SHA256SUMS").read_bytes(),
            before["manifest"],
            "the bundle manifest was rewritten",
        )

    def test_build_fails_closed_when_interpreter_is_unusable(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = self._sandbox(base)
            stub_dir = self._stub_bin(base, STUB_UNUSABLE)
            log = base / "stub.log"
            before = self._snapshot(repo)
            result = self._run_build(
                repo,
                str(stub_dir) + os.pathsep + os.environ.get("PATH", ""),
                log,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("3.9", result.stdout + result.stderr)
            self.assertTrue(log.exists(), "the interpreter stub was never invoked")
            self._assert_bundle_intact(repo, before)

    def test_build_fails_closed_when_interpreter_reports_old_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = self._sandbox(base)
            stub_dir = self._stub_bin(base, STUB_TOO_OLD)
            log = base / "stub.log"
            before = self._snapshot(repo)
            result = self._run_build(
                repo,
                str(stub_dir) + os.pathsep + os.environ.get("PATH", ""),
                log,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("3.9", result.stdout + result.stderr)
            self.assertTrue(log.exists(), "the interpreter stub was never invoked")
            self.assertIn(
                "version_info",
                log.read_text(encoding="utf-8"),
                "the version probe was never run",
            )
            self._assert_bundle_intact(repo, before)

    def test_build_fails_closed_when_no_interpreter_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = self._sandbox(base)
            minimal = base / "minimal"
            minimal.mkdir()
            dirname_stub = minimal / "dirname"
            dirname_stub.write_bytes(STUB_DIRNAME)
            dirname_stub.chmod(0o755)
            probe = subprocess.run(
                [BASH, "-c", "command -v python3 python py || true"],
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": str(minimal)},
            )
            if probe.stdout.strip():
                self.skipTest(
                    "a python interpreter stays reachable under a minimal PATH"
                )
            log = base / "stub.log"
            before = self._snapshot(repo)
            result = self._run_build(repo, str(minimal), log)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("3.9", result.stdout + result.stderr)
            self._assert_bundle_intact(repo, before)


if __name__ == "__main__":
    unittest.main()
