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
