import json
import tempfile
import unittest
from pathlib import Path

import test_runtime


READ_ONLY_MODES = ["answer", "research", "plan-only", "review-only", "security-review"]
MUTATIONS = [
    {"tool_name": "write_to_file", "tool_input": {"TargetFile": "src/file.py"}},
    {"tool_name": "replace_file_content", "tool_input": {"target_file": "src/file.py"}},
]
MUTATIONS += [
    {"tool_name": "run_command", "tool_input": {"CommandLine": command}}
    for command in [
        "touch file", "mkdir directory", "rm file", "mv a b", "cp a b", "git add file",
        "git commit -m x", "git push", "git merge branch", "git rebase main", "npm install x",
        "npm publish", "pip install x", "python3 -c 'open(\"x\", \"w\")'", "node -c x", "echo x > file",
        "echo x >> file", "git clean -fd",
    ]
]


class ActionLockCorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def init(self, contract):
        result = test_runtime.run_script(
            "init_session.py", None,
            "--task-id", "test-task", "--contract-json", json.dumps(contract), cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.cwd / ".gravitas/sessions/test-task"

    def test_100_plan_only_mutation_cases_are_blocked(self):
        cases = [(mode, mutation) for mode in READ_ONLY_MODES for mutation in MUTATIONS]
        self.assertEqual(len(cases), 100)
        session = self.init({"mode": "plan-only", "objective": "must not write"})
        contract_path = session / "contract.json"
        for index, (mode, mutation) in enumerate(cases):
            contract = json.loads(contract_path.read_text())
            contract["mode"] = mode
            contract_path.write_text(json.dumps(contract))
            with self.subTest(index=index, mode=mode, mutation=mutation["tool_name"]):
                result = test_runtime.run_script("pre_tool.py", mutation, cwd=self.cwd)
                self.assertEqual(json.loads(result.stdout)["decision"], "deny", result.stdout)
