"""Workflow orchestration regressions with no GitHub or model calls."""
import fnmatch
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflow(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def events(document):
    return document.get("on", document.get(True))


class VerificationWorkflowTests(unittest.TestCase):
    def test_full_gate_runs_on_feature_pushes(self):
        triggers = events(workflow("gravitas.yml"))
        self.assertIn("push", triggers)
        push = triggers["push"] or {}
        branches = push.get("branches", ["**"])
        self.assertTrue(any(fnmatch.fnmatch("ascension/phase-b-foundation", pattern) for pattern in branches))
        self.assertIn("pull_request", triggers)
        self.assertIn("workflow_dispatch", triggers)

    def test_validation_workflows_request_read_only_token(self):
        for name in ("gravitas.yml", "verify-skill.yml"):
            with self.subTest(name=name):
                self.assertEqual(workflow(name).get("permissions"), {"contents": "read"})

    def test_node_is_explicit_and_current_python_is_tested(self):
        job = workflow("gravitas.yml")["jobs"]["gravitas-verify"]
        versions = [str(version) for version in job["strategy"]["matrix"]["python-version"]]
        self.assertIn("3.9", versions)
        self.assertIn("3.12", versions)
        self.assertIn("3.14", versions)
        self.assertTrue(any(step.get("uses", "").startswith("actions/setup-node@") for step in job["steps"]))

    def test_package_smoke_uses_fresh_environment_and_shared_checker(self):
        steps = workflow("gravitas.yml")["jobs"]["gravitas-verify"]["steps"]
        step = next(item for item in steps if item.get("name") == "Package build and clean install smoke test")
        self.assertIn("-m venv", step["run"])
        self.assertIn("check_installed_package.py", step["run"])
        self.assertNotIn("--no-deps", step["run"])
        self.assertIn("RUNNER_TEMP", step["run"])

    def test_contributor_automation_remains_default_branch_only(self):
        self.assertEqual(events(workflow("sync-contributors.yml"))["push"]["branches"], ["main", "master"])

    def test_inline_scripts_are_syntactically_valid_and_do_not_interpolate_expressions(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash is required for workflow syntax checks")
        for path in WORKFLOWS.glob("*.yml"):
            document = yaml.safe_load(path.read_text())
            for job in document["jobs"].values():
                for step in job.get("steps", []):
                    if "run" not in step:
                        continue
                    with self.subTest(workflow=path.name, step=step.get("name")):
                        self.assertNotIn("${{", step["run"])
                        result = subprocess.run([bash, "-n"], input=step["run"], text=True, capture_output=True)
                        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(shutil.which("bash"), "bash is required for workflow execution")
class ContributorWorkflowTests(unittest.TestCase):
    def run_sync_step(self, check_rc=0, sync_rc=0, diff_rc=0):
        steps = workflow("sync-contributors.yml")["jobs"]["sync"]["steps"]
        script = next(step["run"] for step in steps if step.get("name") == "Sync contributor files")
        stubs = r'''
python() {
  printf '%s\n' "$*" >> "$CALLS"
  if [[ "$*" == *"--check"* ]]; then return "$CHECK_RC"; fi
  return "$SYNC_RC"
}
git() {
  printf 'git %s\n' "$*" >> "$CALLS"
  if [[ "$1" == diff ]]; then return "$DIFF_RC"; fi
  return 99
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_file = root / "env"
            calls = root / "calls"
            env = {**os.environ, "GITHUB_ENV": str(env_file), "CALLS": str(calls),
                   "CHECK_RC": str(check_rc), "SYNC_RC": str(sync_rc), "DIFF_RC": str(diff_rc),
                   "GH_TOKEN": "unused-offline-test", "GITHUB_REPOSITORY_OWNER": "owner",
                   "GITHUB_REPOSITORY": "owner/repository"}
            env.pop("IN_SYNC", None)
            result = subprocess.run([shutil.which("bash"), "--noprofile", "--norc", "-eo", "pipefail", "-c", stubs + script],
                                    env=env, cwd=root, text=True, capture_output=True)
            return result, env_file.read_text() if env_file.exists() else "", calls.read_text() if calls.exists() else ""

    def test_drift_runs_generation_and_exports_changed_state(self):
        result, state, calls = self.run_sync_step(check_rc=1, diff_rc=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("IN_SYNC=0", state)
        self.assertTrue(any("sync_contributors.py" in call and "--check" not in call for call in calls.splitlines()), calls)

    def test_unchanged_files_export_in_sync(self):
        result, state, _ = self.run_sync_step()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("IN_SYNC=1", state)

    def test_generator_failure_stops_without_success_state(self):
        result, state, _ = self.run_sync_step(check_rc=2, sync_rc=2)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(state, "")

    def test_git_failure_is_not_misclassified_as_drift(self):
        result, state, _ = self.run_sync_step(diff_rc=128)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(state, "")

    def test_commit_failures_are_not_silently_accepted(self):
        steps = workflow("sync-contributors.yml")["jobs"]["sync"]["steps"]
        script = next(step["run"] for step in steps if step.get("name") == "Open update PR and trigger its CI")
        self.assertNotIn("|| exit 0", script)


@unittest.skipUnless(shutil.which("bash"), "bash is required for workflow execution")
class ContributorCapabilityTests(unittest.TestCase):
    def capability_step(self, create_allowed="false", auto_merge="false", api_status=0):
        steps = workflow("sync-contributors.yml")["jobs"]["sync"]["steps"]
        step = next((step for step in steps if step.get("id") == "capabilities"), None)
        self.assertIsNotNone(step, "contributor workflow needs capability preflight")
        stubs = r'''
gh() {
  if [ "$API_STATUS" != 0 ]; then return "$API_STATUS"; fi
  if [[ "$*" == *actions/permissions/workflow* ]]; then
    printf '%s\n' "$CREATE_ALLOWED"
  else
    printf '%s\n' "$AUTO_MERGE"
  fi
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, summary = root / "output", root / "summary"
            env = {**os.environ, "GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary),
                   "CREATE_ALLOWED": create_allowed, "AUTO_MERGE": auto_merge,
                   "API_STATUS": str(api_status), "GITHUB_REPOSITORY": "owner/repo"}
            result = subprocess.run([shutil.which("bash"), "--noprofile", "--norc", "-eo", "pipefail", "-c", stubs + step["run"]],
                                    cwd=root, env=env, text=True, capture_output=True)
            return result, output.read_text() if output.exists() else "", summary.read_text() if summary.exists() else ""

    def test_disabled_bot_capabilities_are_explicit_and_do_not_error(self):
        result, output, summary = self.capability_step()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("create_pr=false", output)
        self.assertIn("auto_merge=false", output)
        self.assertIn("patch", summary)

    def test_enabled_capabilities_are_preserved(self):
        result, output, _ = self.capability_step(create_allowed="true", auto_merge="true")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("create_pr=true", output)
        self.assertIn("auto_merge=true", output)

    def test_unreadable_capabilities_fall_back_without_privilege_escalation(self):
        result, output, summary = self.capability_step(api_status=403)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("create_pr=false", output)
        self.assertIn("auto_merge=false", output)
        self.assertIn("patch", summary)

    def test_creation_and_merge_respect_capabilities_and_patch_is_retained(self):
        steps = workflow("sync-contributors.yml")["jobs"]["sync"]["steps"]
        creation = next(step for step in steps if step.get("id") == "openpr")
        merge = next(step for step in steps if step.get("name") == "Enable auto-merge on green")
        self.assertIn("steps.capabilities.outputs.create_pr == 'true'", creation["if"])
        self.assertIn("steps.capabilities.outputs.auto_merge == 'true'", merge["if"])
        upload = next((step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@")), None)
        self.assertIsNotNone(upload)
        self.assertEqual(upload["with"]["name"], "contributor-update")


if __name__ == "__main__":
    unittest.main()
