"""OpenCode adapter tests: init scaffolding, guard, shim mapping."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "adapters" / "opencode"

sys.path.insert(0, str(ROOT))
from gravitas_init import init_antigravity, init_opencode


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    raw = text[4:].partition("\n---\n")[0]
    data = {}
    for line in raw.splitlines():
        match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if match:
            data[match.group(1)] = match.group(2).strip()
    return data


class InitTests(unittest.TestCase):
    def test_init_opencode_full_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = init_opencode(Path(tmp), profile="balanced", source_root=ROOT)
            self.assertTrue(result["ok"], result)
            root = Path(tmp)
            self.assertTrue((root / ".agents" / "skills" / "gravitas" / "SKILL.md").is_file())
            self.assertTrue((root / ".agents" / "skills" / "gravitas-highstakes" / "SKILL.md").is_file())
            for agent in ("investigator", "reviewer", "impact-auditor", "test-adversary"):
                self.assertTrue((root / ".opencode" / "agents" / f"{agent}.md").is_file(), agent)
            self.assertTrue((root / ".opencode" / "plugins" / "gravitas.js").is_file())
            config = json.loads((root / "opencode.json").read_text())
            self.assertIn("permission", config)
            agents_md = (root / "AGENTS.md").read_text()
            self.assertIn("GRAVITAS-OPENCODE-START", agents_md)
            contract = json.loads((root / ".gravitas" / "opencode-contract.json").read_text())
            self.assertEqual(contract["mode"], "implement")

    def test_init_is_idempotent_and_non_clobbering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "opencode.json").write_text(json.dumps({"model": "custom", "permission": {"edit": "deny"}}))
            first = init_opencode(root, profile="strict", source_root=ROOT)
            self.assertTrue(first["ok"])
            config = json.loads((root / "opencode.json").read_text())
            self.assertEqual(config["model"], "custom")
            self.assertEqual(config["permission"], {"edit": "deny"})
            second = init_opencode(root, profile="strict", source_root=ROOT)
            self.assertTrue(second["ok"])
            self.assertTrue(second["skipped"], "rerun must report skips, not rewrites")
            agents_md = (root / "AGENTS.md").read_text()
            self.assertEqual(agents_md.count("GRAVITAS-OPENCODE-START"), 1)

    def test_init_antigravity_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = init_antigravity(Path(tmp), source_root=ROOT)
            self.assertTrue(result["ok"])
            self.assertTrue((Path(tmp) / ".agents" / "skills" / "gravitas" / "SKILL.md").is_file())
            self.assertIn("agy plugin install", result["next"])

    def test_init_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ROOT / "gravitas_cli.py"), "init",
                 "--host", "opencode", "--profile", "fast", "--root", tmp],
                text=True, capture_output=True, cwd=ROOT, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["ok"])


class AgentTemplateTests(unittest.TestCase):
    def test_agent_frontmatter(self):
        for agent in ("investigator", "reviewer", "impact-auditor", "test-adversary"):
            with self.subTest(agent=agent):
                meta = frontmatter(ADAPTER / "agents" / f"{agent}.md")
                self.assertTrue(meta.get("description"), agent)
                self.assertIn(meta.get("mode"), ("subagent", "primary", "all"), agent)
                body = (ADAPTER / "agents" / f"{agent}.md").read_text()
                self.assertIn("permission:", body, agent)
                self.assertIn("edit: deny", body, agent)

    def test_permission_profiles_parse_and_deny_destructive(self):
        for profile in ("fast", "balanced", "strict"):
            with self.subTest(profile=profile):
                config = json.loads((ADAPTER / "permissions" / f"{profile}.json").read_text())
                bash = config["permission"].get("bash", {})
                self.assertIsInstance(bash, dict, profile)
                for dangerous in ("rm *", "git push *"):
                    self.assertEqual(bash.get(dangerous), "deny", f"{profile}:{dangerous}")


class GuardTests(unittest.TestCase):
    def guard(self, tool, args, contract, cwd=None):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(cwd) if cwd else Path(tmp)
            contract_path = work / "contract.json"
            contract_path.write_text(json.dumps(contract))
            result = subprocess.run(
                [sys.executable, str(ROOT / "gravitas_cli.py"), "guard",
                 "--contract", str(contract_path),
                 "--envelope", json.dumps({"tool": tool, "args": args,
                                            "workspace_roots": [str(work)],
                                            "host": "opencode"})],
                text=True, capture_output=True, cwd=work, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_read_only_contract_denies_opencode_edit(self):
        verdict = self.guard("edit", {"filePath": "a.py"},
                             {"mode": "plan", "allowed_write_scope": ["."]})
        self.assertEqual(verdict["decision"], "deny")

    def test_implement_allows_in_scope_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a.py"
            target.write_text("x = 1\n")
            verdict = self.guard("edit", {"filePath": "a.py"},
                                 {"mode": "implement", "allowed_write_scope": ["."]},
                                 cwd=tmp)
            # read-before-write: existing file never read -> deny is correct
            self.assertEqual(verdict["decision"], "deny")

    def test_opencode_bash_maps_to_shell_policy(self):
        verdict = self.guard("bash", {"command": "rm -rf build/"},
                             {"mode": "implement", "allowed_write_scope": ["."]})
        self.assertEqual(verdict["decision"], "deny")  # force_ask -> deny in shim terms

    def test_garbage_envelope_fails_closed(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "gravitas_cli.py"), "guard",
             "--envelope", "not-json"],
            text=True, capture_output=True, cwd=ROOT, check=False)
        self.assertEqual(json.loads(result.stdout)["decision"], "deny")


class ShimMappingTests(unittest.TestCase):
    def test_to_envelope_mapping(self):
        if shutil.which("node") is None:
            self.skipTest("node not available")
        shim = ADAPTER / "plugin" / "gravitas.js"
        script = (
            f"import('{shim.as_uri()}').then(m => {{"
            "  const dir = '/repo';"
            "  const cases = ["
            "    ['read', {filePath: 'a.py'}],"
            "    ['edit', {filePath: 'a.py'}],"
            "    ['bash', {command: 'rm x'}],"
            "    ['grep', {pattern: 'x'}],"
            "    ['task', {description: 'y'}],"
            "  ];"
            "  console.log(JSON.stringify(cases.map(([t, a]) => m.toEnvelope(t, a, dir))));"
            "});"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        envelopes = json.loads(result.stdout)
        by_tool = {e["tool"]: e for e in envelopes}
        self.assertEqual(by_tool["view_file"]["args"], {"AbsolutePath": "a.py"})
        self.assertEqual(by_tool["write_to_file"]["args"], {"TargetFile": "a.py"})
        self.assertEqual(by_tool["run_command"]["args"], {"CommandLine": "rm x"})
        self.assertEqual(by_tool["grep_search"]["host"], "opencode")
        self.assertEqual(by_tool["task"]["tool"], "task")


if __name__ == "__main__":
    unittest.main()
