import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync_mod = load("sync_contributors", ROOT / "scripts/sync_contributors.py")


class DenylistParityTests(unittest.TestCase):
    def test_prohibited_phrases_match_claims_gate(self):
        gate_src = (ROOT / "scripts/check_readme_claims.py").read_text(encoding="utf-8")
        for phrase in sync_mod.PROHIBITED_PHRASES:
            self.assertIn(phrase, gate_src, f"sync filter phrase missing from claims gate: {phrase}")
        gate_phrases = [
            "gap closure",
            "Functional Solve Rate",
            "false completion rate",
            "99% Claude",
            "Claude replacement",
            "better than Claude",
            "Claude-like",
            "like Claude",
            "forces Gemini",
            "competitive with Claude",
        ]
        for phrase in gate_phrases:
            self.assertIn(phrase, sync_mod.PROHIBITED_PHRASES)


class SanitizeTests(unittest.TestCase):
    def test_clean_title_kept(self):
        self.assertEqual(sync_mod.sanitize_title("fix(paths): canonicalize at record time"), "fix(paths): canonicalize at record time")

    def test_prohibited_title_rejected(self):
        self.assertEqual(sync_mod.sanitize_title("Claude-like reviewer agent"), "")
        self.assertEqual(sync_mod.sanitize_title("better than Claude at reviews"), "")

    def test_long_title_truncated(self):
        self.assertTrue(len(sync_mod.sanitize_title("x" * 200)) <= 80)

    def test_credit_falls_back_to_numbers(self):
        prs = [{"number": 7, "title": "Claude-like helper", "merged_at": "2026-01-01T00:00:00Z"}]
        self.assertEqual(sync_mod.credit_for(prs), "contributions via #7")


class SyncBehaviorTests(unittest.TestCase):
    README = """# T

## Contributors

| [![A](https://github.com/alice.png?size=100)](https://github.com/alice) |
|:---:|
| [A](https://github.com/alice) |
| maintainer |

<br />

## Next

body
"""
    MD = """# Contributors

Thanks.

- Alice ([@alice](https://github.com/alice)) — maintainer
"""

    def test_existing_entries_byte_identical_after_sync(self):
        names = {"alice": "A", "bob": "Bob B"}
        prs = {"bob": [{"number": 9, "title": "fix docs typo", "merged_at": "2026-02-01T00:00:00Z"}]}
        new_readme, new_md, fresh = sync_mod.sync(self.README, self.MD, ["alice", "bob"], prs, dict(names), "alice")
        self.assertEqual(fresh, ["bob"])
        self.assertIn("- Alice ([@alice](https://github.com/alice)) — maintainer\n", new_md)
        self.assertIn("| maintainer |", new_readme)
        self.assertIn("https://github.com/bob.png?size=100", new_readme)
        self.assertIn("Bob B ([@bob](https://github.com/bob)) — contributions via #9 “fix docs typo”", new_md)
        # Idempotency: syncing the output changes nothing.
        again_r, again_m, again_f = sync_mod.sync(new_readme, new_md, ["alice", "bob"], prs, dict(names), "alice")
        self.assertEqual((again_r, again_m, again_f), (new_readme, new_md, []))

    def test_newcomer_order_by_first_merge(self):
        prs = {
            "zara": [{"number": 11, "title": "b", "merged_at": "2026-03-01T00:00:00Z"}],
            "mig": [{"number": 10, "title": "a", "merged_at": "2026-01-01T00:00:00Z"}],
        }
        _, _, fresh = sync_mod.sync(self.README, self.MD, ["alice", "zara", "mig"], prs, {"alice": "A"}, "alice")
        self.assertEqual(fresh, ["mig", "zara"])

    def test_owner_stays_first(self):
        _, new_md, _ = sync_mod.sync(self.README, self.MD, ["bob", "alice"], {}, {"alice": "A", "bob": "B"}, "alice")
        bullets = [l for l in new_md.splitlines() if l.startswith("- ")]
        self.assertTrue(bullets[0].startswith("- Alice"))


class CheckModeTests(unittest.TestCase):
    def test_check_mode_exit_codes_on_real_tree(self):
        here = [sys.executable, str(ROOT / "scripts/sync_contributors.py")]
        env = {"GITHUB_REPOSITORY_OWNER": "udaysharmadev", "PATH": "/usr/bin:/bin"}
        with tempfile.TemporaryDirectory() as tmp:
            cands = Path(tmp) / "c.json"
            prs = Path(tmp) / "p.json"
            names = Path(tmp) / "n.json"
            cands.write_text(json.dumps(["udaysharmadev"]), encoding="utf-8")
            prs.write_text(json.dumps({}), encoding="utf-8")
            names.write_text(json.dumps({"udaysharmadev": "Uday Sharma"}), encoding="utf-8")
            # Unknown owner relative to the real README wall -> would change.
            r = subprocess.run(
                here + ["--owner", "someone-new", "--contributors-json", str(cands),
                        "--prs-json", str(prs), "--names-json", str(names), "--check"],
                capture_output=True, text=True, env={**env}, cwd=str(ROOT),
            )
            self.assertEqual(r.returncode, 1)
            # Real owner set matching the wall -> in sync only if wall already lists them;
            # just assert the script runs and reports deterministically.
            r2 = subprocess.run(
                here + ["--owner", "udaysharmadev", "--contributors-json", str(cands),
                        "--prs-json", str(prs), "--names-json", str(names), "--check"],
                capture_output=True, text=True, env={**env}, cwd=str(ROOT),
            )
            self.assertIn(r2.stdout.strip(), ("contributors in sync",))
            self.assertEqual(r2.returncode, 0)


if __name__ == "__main__":
    unittest.main()
