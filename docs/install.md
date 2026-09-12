# Install GRAVITAS

GRAVITAS has two modes. **Core** is the portable Agent Skill. **Native** is a
separate Antigravity plugin that packages Core with hook-based workflow checks.

## Core (recommended)

From the project where you use Antigravity IDE:

```bash
npx skills add udaysharmadev/Gravitas --skill gravitas --agent antigravity --yes
```

For Antigravity CLI (`agy`), replace `antigravity` with `antigravity-cli`.
The command creates `.agents/skills/gravitas/` in the current project. This is
project-scoped on purpose: current IDE and CLI global paths differ across
Antigravity releases.

Verify the installed files and canonical hash:

```bash
python3 .agents/skills/gravitas/scripts/doctor.py
```

Update Core with:

```bash
npx skills update gravitas --project --yes
```

Remove it with:

```bash
npx skills remove gravitas --project --agent antigravity --yes
```

## Native (Antigravity hooks)

Native uses the local-plugin install workflow documented by Google. Clone the
repository, build the checked-in distributable bundle, then install that exact
directory:

```bash
git clone --depth 1 https://github.com/udaysharmadev/Gravitas.git
cd Gravitas
bash scripts/build-native-bundle.sh
agy plugin install "$PWD/dist/gravitas-antigravity"
```

Validate the local bundle before installing, then confirm it is staged:

```bash
agy plugin validate "$PWD/dist/gravitas-antigravity"
agy plugin list
```

Validation reports the processed skills, agents, and hooks. The list should
include `gravitas-native`; in the Antigravity CLI TUI, `/hooks` shows loaded hooks.

To refresh Native, pull the repository, rebuild, and run the same local
`agy plugin install` command again. The Antigravity CLI v1.2.1 behavior used in
our verification restaged the existing bundle. To uninstall:

```bash
agy plugin uninstall gravitas-native
```

## Troubleshooting

- `npx` unavailable: install a current Node.js/npm release, then rerun Core.
- `agy` unavailable: install Antigravity CLI using [Google’s instructions](https://antigravity.google/docs/cli/install/), and make sure its binary directory is on `PATH`.
- Core not visible: start a new Antigravity conversation and ask which skills are available. Antigravity discovers workspace skills from `.agents/skills/`.
- Native absent from `agy plugin list`: rerun the build command, then pass the absolute `dist/gravitas-antigravity` path to `agy plugin install`.
- Hooks not visible: use `/hooks` in the CLI TUI; plugin staging alone is not a substitute for a new CLI session.

Native hooks are workflow enforcement, not an OS sandbox. Keep Antigravity’s
own permissions and sandboxing enabled for untrusted code. See [SECURITY.md](../SECURITY.md).
