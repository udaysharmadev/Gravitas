"""Regression coverage for the portable skill verification runner."""
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
VERIFY_SCRIPT = ROOT / "skills" / "gravitas" / "scripts" / "verify.py"


def load_verify_module():
    spec = importlib.util.spec_from_file_location("skill_verify", VERIFY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = load_verify_module()


class PythonFallbackTests(unittest.TestCase):
    def test_python_fallback_uses_the_running_interpreter(self):
        command = verify.FALLBACK_CHAINS["python"]
        self.assertEqual(command, f'"{sys.executable}" -m pytest -q')
        self.assertNotIn("python3", command)

        success, output = verify.run_verification(
            f'"{sys.executable}" -c "import sys; sys.exit(0)"'
        )
        self.assertTrue(success, output)


if __name__ == "__main__":
    unittest.main()
