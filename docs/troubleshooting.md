# Troubleshooting

For the tested commands, see [install.md](install.md).

| Symptom | Check | Resolution |
|---|---|---|
| `npx` is not found | `node --version` and `npm --version` | Install a current Node.js/npm release, then rerun the Core install command. |
| Core is not visible | `python3 .agents/skills/gravitas/scripts/doctor.py` | Confirm the command was run from the project where you use Antigravity. Start a new conversation and ask which skills are available. |
| `agy` is not found | `agy --version` | Follow [Google’s CLI installation guide](https://antigravity.google/docs/cli/install/) and ensure the installed binary directory is on `PATH`. |
| Native is not listed | `agy plugin validate "$PWD/dist/gravitas-antigravity"` | Rebuild with `bash scripts/build-native-bundle.sh`, validate the bundle, then install the absolute bundle path. |
| Hooks are not shown | `/hooks` in a new `agy` TUI session | Confirm `agy plugin list` includes `gravitas-native`; restart the CLI session after installation. |

Do not manually delete broad Antigravity configuration directories. Remove Native
with `agy plugin uninstall gravitas-native`; Core removal is documented in
[install.md](install.md).

## Runtime failure modes

| Symptom | Check | Resolution |
|---|---|---|
| `gravitas doctor` fails after `pip install` | run it outside the repo checkout | Reinstall; `mode` must be `installed`. If `unresolved`, the wheel lacks `share/gravitas` assets. |
| Stop gate loops `continue` after edits | `gravitas explain --session-dir <dir>` | Evidence predating the final mutation is stale by design; re-run validators after the last edit. |
| `force_ask` on every `mv`/infra command | expected policy | Destructive capability requires confirmation (Antigravity) or is hard-denied (OpenCode shim). Narrow the command or amend scope. |
| OpenCode shim allows everything | `gravitas guard` manually | `gravitas`/python3 missing from PATH degrades to allow-with-warning. Install both; check `gravitas doctor`. |
| `gravitas init` skipped files | `installed` vs `skipped` in output | Existing files are never overwritten. Diff and merge manually. |
| `gravitas bench run` exits 2 | output JSON | No model credentials: episode recorded INVALID (infrastructure), not a solver failure. |
| Hook denies a legitimate write | `allowed_write_scope` in contract | Read the file first (Rule 1), confirm scope covers it, or amend the contract. |
