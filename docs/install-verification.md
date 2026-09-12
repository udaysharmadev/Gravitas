# Install verification

Tested on **2026-09-12** on macOS 26.3.1 (arm64), Node.js 24.11.0, npm 11.6.1,
skills CLI 1.5.26, and Antigravity CLI (`agy`) 1.2.1. Each Core test used an
empty project under `/private/tmp`; no user project or global Core install was
changed. Native tests installed a uniquely named `gravitas-native` bundle,
inspected it, and removed it in the same run.

| Case | Command / check | Result |
|---|---|---|
| A. Repository discovery | `npx skills@1.5.26 add udaysharmadev/Gravitas --list` | PASS — found `gravitas`, `gravitas-python`, and `gravitas-typescript`. |
| B. Core install for IDE | `npx skills@1.5.26 add udaysharmadev/Gravitas --skill gravitas --agent antigravity --yes` | PASS — installed `.agents/skills/gravitas`. |
| C. Core payload | Checked `SKILL.md`, `scripts/verify.sh`, and `references/verification.md` | PASS — all present. |
| D. Core discovery metadata | `npx skills@1.5.26 list --agent antigravity --json` | PASS — project skill named `gravitas`, agent `Antigravity`. |
| E. Core update | `npx skills@1.5.26 update gravitas --project --yes` | PASS — a clean project updated one `gravitas` skill from the published GitHub commit. |
| F. Core removal | `npx skills@1.5.26 remove gravitas --project --agent antigravity --yes` | PASS — installed skill removed. |
| G. Native build | `bash scripts/build-native-bundle.sh` | PASS — root manifest, hooks, Core `SKILL.md`, and runtime scripts present. |
| H. Native plugin install/discovery | `agy plugin validate /absolute/path/dist/gravitas-antigravity`; `agy plugin install …`; `agy plugin list` | PASS — validator and install reported 1 skill, 3 agents, and 1 hook set; the list showed `gravitas-native` staged. |
| I. Native refresh | Re-ran the same local `agy plugin install` command | PASS — bundle restaged with the same components. |
| J. Native uninstall | `agy plugin uninstall gravitas-native` | PASS — bundle removed; no unrelated plugin was removed. |
| K. Agent Skills validation | `npx skills-ref validate skills/gravitas` | PASS — `Valid skill: skills/gravitas`. |
| L. Doctor | `python3 skills/gravitas/scripts/doctor.py` | PASS — reports Core hash, `agy` availability, Native plugin discovery, enabled state, and hooks when a compatible plugin is installed. |

## Boundaries

Native install/list proves Antigravity CLI accepted and staged the bundle. It
does not claim a live model trajectory or OS security sandbox test. Use `/hooks`
inside a new CLI session to inspect active hook registration.
