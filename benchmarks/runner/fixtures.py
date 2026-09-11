"""Disposable deterministic fixtures for implementation-episode plumbing.

These fixtures test the runner, not the product claims of GravitasBench.  Each
task gets an isolated worktree and a task-specific acceptance test; real,
licensed repositories can replace this factory without changing the runner.
"""
import shutil
from pathlib import Path


CASES = (
    ("normalize", "def transform(value):\n    return value\n", "self.assertEqual(transform('  Mixed Case  '), 'mixed case')"),
    ("deduplicate", "def transform(value):\n    return value\n", "self.assertEqual(transform(['b', 'a', 'b']), ['a', 'b'])"),
    ("redact", "def transform(value):\n    return value\n", "self.assertEqual(transform({'token': 'secret', 'name': 'Ada'}), {'token': '[redacted]', 'name': 'Ada'})"),
    ("clamp", "def transform(value):\n    return value\n", "self.assertEqual(transform(-3), 0)"),
    ("slug", "def transform(value):\n    return value\n", "self.assertEqual(transform('Hello, World!'), 'hello-world')"),
)


def case_for(task_id):
    return CASES[sum(ord(char) for char in task_id) % len(CASES)]


def materialize(task_id, destination):
    """Create a clean, intentionally failing fixture and return its metadata."""
    destination = Path(destination)
    if destination.exists():
        shutil.rmtree(destination)
    (destination / "src").mkdir(parents=True)
    (destination / "tests").mkdir()
    name, implementation, assertion = case_for(task_id)
    (destination / "src" / "target.py").write_text(implementation)
    (destination / "tests" / "test_target.py").write_text(
        "import sys\nimport unittest\nfrom pathlib import Path\n\n"
        "sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))\n"
        "from target import transform\n\n"
        "class TargetTests(unittest.TestCase):\n"
        "    def test_expected_behavior(self):\n"
        f"        {assertion}\n"
    )
    return {"fixture_kind": name, "allowed_write_scope": ["src/target.py"], "validator": "python -m unittest discover -s tests -v"}
