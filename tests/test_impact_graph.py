"""impact_graph path normalization must never accept paths outside the repo root."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "plugins/gravitas-antigravity/scripts"))

from impact_graph import _normalize_changed, build_impact_graph


class NormalizeChangedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        self.root = base / "repo"
        (self.root / "sub").mkdir(parents=True)
        (self.root / "module.py").write_text("x = 1\n")
        (self.root / "sub" / "inner.py").write_text("y = 2\n")
        self.outside = base / "outside_probe.txt"
        self.outside.write_text("secret\n")

    def test_dotdot_escape_is_rejected(self):
        self.assertIsNone(_normalize_changed(self.root, "../outside_probe.txt"))

    def test_nested_dotdot_escape_is_rejected(self):
        self.assertIsNone(_normalize_changed(self.root, "sub/../../outside_probe.txt"))

    def test_absolute_outside_is_rejected(self):
        self.assertIsNone(_normalize_changed(self.root, str(self.outside)))

    def test_symlink_pointing_outside_is_rejected(self):
        link = self.root / "link.txt"
        try:
            link.symlink_to(self.outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertIsNone(_normalize_changed(self.root, "link.txt"))

    def test_in_root_relative_and_absolute_still_normalize(self):
        self.assertEqual(_normalize_changed(self.root, "module.py"), "module.py")
        self.assertEqual(_normalize_changed(self.root, str(self.root / "module.py")), "module.py")
        self.assertEqual(_normalize_changed(self.root, "sub/inner.py"), "sub/inner.py")
        self.assertEqual(_normalize_changed(self.root, r"sub\inner.py"), "sub/inner.py")
        self.assertEqual(_normalize_changed(self.root, str(self.root / "sub" / "inner.py")),
                         "sub/inner.py")

    def test_in_root_dotdot_that_stays_inside_normalizes(self):
        self.assertEqual(_normalize_changed(self.root, "sub/../module.py"), "module.py")

    def test_missing_file_is_none(self):
        self.assertIsNone(_normalize_changed(self.root, "nope.py"))

    def test_build_impact_graph_has_no_escaping_keys(self):
        graph, _ = build_impact_graph(self.root, ["../outside_probe.txt", "module.py"])
        self.assertNotIn("../outside_probe.txt", graph)
        self.assertTrue(all(not key.startswith("..") for key in graph))
        self.assertIn("module.py", graph)

    def test_build_impact_graph_keeps_deleted_in_root_files(self):
        graph, _ = build_impact_graph(self.root, ["gone.py"])
        self.assertIn("gone.py", graph)

    def test_build_impact_graph_drops_absolute_outside_paths(self):
        graph, _ = build_impact_graph(self.root, [str(self.outside)])
        self.assertEqual(graph, {})


if __name__ == "__main__":
    unittest.main()
