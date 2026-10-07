"""Host adapter tests: Antigravity fixtures, aliases, bundle surfaces."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins" / "gravitas-antigravity" / "scripts"

import sys
sys.path.insert(0, str(SCRIPTS))

from gravitas_action import antigravity_envelope, canonical_tool, normalize

FIXTURES = ROOT / "tests" / "fixtures" / "antigravity"
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def load(name):
    return json.loads((FIXTURES / name).read_text())


class AntigravityFixtureTests(unittest.TestCase):
    def test_ide_list_dir_normalizes_to_read(self):
        envelope, action = antigravity_envelope(load("pretooluse-ide.json"))
        self.assertEqual(envelope.host, "antigravity")
        self.assertEqual(envelope.event, "PreToolUse")
        self.assertEqual(envelope.conversation_id, "8591815f-ddcd-42e2-a41f-4d5a7a03091b")
        self.assertEqual(envelope.workspace_roots, ["/Users/dev/work/hooks"])
        self.assertEqual(action.kind, "read")
        self.assertEqual(action.mutation, "none")

    def test_cli_destructive_shell(self):
        envelope, action = antigravity_envelope(load("pretooluse-cli.json"))
        self.assertEqual(action.kind, "execute")
        self.assertEqual(action.mutation, "destructive")
        self.assertEqual(action.executable, "rm")

    def test_legacy_preview_shape(self):
        envelope, action = antigravity_envelope(load("pretooluse-legacy.json"))
        self.assertEqual(envelope.tool, "write_to_file")
        self.assertEqual(action.kind, "write")
        self.assertEqual(action.paths, ["src/app.py"])

    def test_posttooluse_shape(self):
        payload = load("posttooluse.json")
        envelope, action = antigravity_envelope(payload)
        self.assertEqual(action.kind, "execute")
        self.assertEqual(payload["error"], "")

    def test_stop_shape(self):
        payload = load("stop.json")
        self.assertTrue(payload["fullyIdle"])
        self.assertEqual(payload["terminationReason"], "NO_TOOL_CALL")


class AliasTests(unittest.TestCase):
    def test_edit_file_alias_writes(self):
        self.assertEqual(canonical_tool("edit_file"), "write_to_file")
        action = normalize("edit_file", {"TargetFile": "a.py"})
        self.assertEqual((action.kind, action.mutation), ("write", "write"))

    def test_unknown_tool_is_visible_not_gated(self):
        action = normalize("future_tool_xyz", {"Anything": 1})
        self.assertEqual(action.kind, "other")
        self.assertEqual(action.mutation, "none")

    def test_list_dir_target(self):
        action = normalize("list_dir", {"DirectoryPath": "/repo/x"})
        self.assertEqual(action.paths, ["/repo/x"])


class BundleSurfaceTests(unittest.TestCase):
    def plugin(self):
        return ROOT / "plugins" / "gravitas-antigravity"

    def test_plugin_manifest_valid(self):
        manifest = json.loads((self.plugin() / "plugin.json").read_text())
        self.assertRegex(manifest["name"], r"^[A-Za-z0-9-_]+$")
        self.assertTrue(manifest.get("description"))

    def test_hooks_json_covers_lifecycle(self):
        hooks = json.loads((self.plugin() / "hooks.json").read_text())
        events = {event for group in hooks.values() if isinstance(group, dict)
                  for event in group}
        for expected in ("PreToolUse", "PostToolUse", "PostInvocation", "Stop"):
            self.assertIn(expected, events)

    def test_no_workflows_directory(self):
        self.assertFalse((ROOT / ".agents" / "workflows").exists(),
                         "legacy workflows must be migrated to skills")

    def test_skill_frontmatter(self):
        for skill in ("gravitas", "gravitas-highstakes"):
            text = (ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertTrue(text.startswith("---\n"), skill)
            frontmatter = text[4:].partition("\n---\n")[0]
            name = re.search(r"^name:\s*(\S+)", frontmatter, re.M).group(1)
            self.assertTrue(SKILL_NAME.match(name), name)
            self.assertEqual(name, skill)
            description = re.search(r"description:\s*>\s*\n((?:  .*\n)+)", frontmatter)
            self.assertTrue(description, skill)
            self.assertLessEqual(
                len(" ".join(description.group(1).split())), 1024, skill)

    def test_rule_frontmatter(self):
        for rule in (self.plugin() / "rules").glob("*.md"):
            frontmatter = rule.read_text()[4:].partition("\n---\n")[0]
            trigger = re.search(r"^trigger:\s*(\S+)", frontmatter, re.M)
            self.assertIn(trigger.group(1),
                          ("always_on", "model_decision", "glob", "manual"), rule.name)


if __name__ == "__main__":
    unittest.main()
