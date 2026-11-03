"""Packaging integrity: the wheel must ship the runtime the CLI checks."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

ROOT = Path(__file__).parents[1]


class PackagingTests(unittest.TestCase):
    def test_data_files_cover_doctor_assets(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
        patterns = [
            pattern
            for group in pyproject["tool"]["setuptools"]["data-files"].values()
            for pattern in group
        ]
        shipped = set()
        for pattern in patterns:
            shipped.update(path.relative_to(ROOT).as_posix() for path in ROOT.glob(pattern))
        for asset in [
            "plugins/gravitas-antigravity/plugin.json",
            "plugins/gravitas-antigravity/hooks.json",
            "plugins/gravitas-antigravity/scripts/pre_tool.py",
            "plugins/gravitas-antigravity/scripts/stop_gate.py",
            "plugins/gravitas-antigravity/scripts/evidence_chain.py",
            "plugins/gravitas-antigravity/scripts/validator_runner.py",
            "plugins/gravitas-antigravity/scripts/gravitas_action.py",
            "plugins/gravitas-antigravity/scripts/gravitas_policy.py",
            "skills/gravitas/SKILL.md",
            "skills/gravitas/SESSION_FAILURES.md",
            "skills/gravitas-highstakes/SKILL.md",
            "plugins/gravitas-antigravity/rules/gravitas-invariants.md",
            "adapters/opencode/contract-template.json",
            "adapters/opencode/plugin/gravitas.js",
            "adapters/opencode/permissions/balanced.json",
        ]:
            self.assertIn(asset, shipped, f"wheel data-files omit {asset}")

    def test_doctor_passes_in_checkout(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "gravitas_cli.py"), "doctor"],
            text=True,
            capture_output=True,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        checks = json.loads(result.stdout)
        self.assertTrue(checks["mode"].startswith("checkout"))
        for key in ("skill", "plugin_manifest", "hooks", "evidence_chain"):
            self.assertTrue(checks[key], key)


class InstalledAssetsTests(unittest.TestCase):
    def resolver(self, module_root, existing, user_root=Path("/isolated/user")):
        import gravitas_cli
        import sysconfig
        user_site = user_root / "lib" / "python" / "site-packages"
        original = sysconfig.get_path

        def scheme_path(name, scheme=None, *args, **kwargs):
            if scheme == "posix_user":
                return str(user_root if name == "data" else user_site)
            return original(name, scheme, *args, **kwargs)

        with patch.object(gravitas_cli, "MODULE_ROOT", module_root), \
             patch.object(sys, "prefix", "/isolated/prefix"), \
             patch.object(sysconfig, "get_scheme_names", return_value=("posix_user",)), \
             patch.object(sysconfig, "get_path", side_effect=scheme_path), \
             patch.object(Path, "is_dir", lambda path: path in existing):
            return gravitas_cli.installed_assets_root()

    def test_user_scheme_is_resolved_for_user_installed_module(self):
        user_root = Path("/isolated/user")
        expected = user_root / "share" / "gravitas"
        self.assertEqual(self.resolver(user_root / "lib/python/site-packages",
                                      {expected / "plugins/gravitas-antigravity/scripts"}), expected)

    def test_user_module_does_not_load_unrelated_prefix_runtime(self):
        user_root = Path("/isolated/user")
        expected = user_root / "share" / "gravitas"
        self.assertEqual(self.resolver(user_root / "lib/python/site-packages", {
            expected / "plugins/gravitas-antigravity/scripts",
            Path("/isolated/prefix/share/gravitas/plugins/gravitas-antigravity/scripts"),
        }), expected)

    def test_prefix_module_keeps_prefix_runtime(self):
        expected = Path("/isolated/prefix/share/gravitas")
        self.assertEqual(self.resolver(Path("/isolated/prefix/lib/python/site-packages"), {
            expected / "plugins/gravitas-antigravity/scripts",
            Path("/isolated/user/share/gravitas/plugins/gravitas-antigravity/scripts"),
        }), expected)

    def test_unrelated_module_does_not_search_user_runtime(self):
        self.assertIsNone(self.resolver(Path("/another/location"), {
            Path("/isolated/user/share/gravitas/plugins/gravitas-antigravity/scripts"),
        }))

    def test_user_module_missing_assets_does_not_fall_back_to_other_install(self):
        self.assertIsNone(self.resolver(Path("/isolated/user/lib/python/site-packages"), {
            Path("/isolated/prefix/share/gravitas/plugins/gravitas-antigravity/scripts"),
        }))


if __name__ == "__main__":
    unittest.main()
