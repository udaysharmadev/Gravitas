"""cargo verbs that run project code must not classify as read-only."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "plugins/gravitas-antigravity/scripts"))

from gravitas_action import classify_shell


class CargoClassificationTests(unittest.TestCase):
    def test_cargo_check_runs_build_scripts_and_is_mutation(self):
        for command in ("cargo check", "cargo check --all", "cargo check -p foo --release",
                        "cargo c", "cd crate && cargo check"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "mutation", command)

    def test_cargo_test_and_run_stay_mutation(self):
        for command in ("cargo test", "cargo run", "cargo build"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "mutation", command)

    def test_other_package_manager_check_verbs_stay_read_only(self):
        for command in ("pip check", "yarn check", "pip list", "cargo --version"):
            with self.subTest(command=command):
                self.assertEqual(classify_shell(command)["mutation"], "none", command)


if __name__ == "__main__":
    unittest.main()
