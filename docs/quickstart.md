# Quickstart

Gravitas in 60 seconds, per host. Research preview: comparative
performance is not yet measured.

## Antigravity Core (portable skill, recommended start)

```bash
npx skills add udaysharmadev/Gravitas --skill gravitas --agent antigravity --yes
python3 .agents/skills/gravitas/scripts/doctor.py
```

Say: `Use Gravitas to fix this bug and verify the result.`

## Antigravity Native (hook enforcement)

```bash
git clone --depth 1 https://github.com/udaysharmadev/Gravitas.git
cd Gravitas
bash scripts/build-native-bundle.sh
agy plugin install "$PWD/dist/gravitas-antigravity"
agy plugin validate "$PWD/dist/gravitas-antigravity"
```

## OpenCode

Requires `gravitas` on PATH (`pip install gravitas`) and python3.

```bash
cd your-project
gravitas init --host opencode --profile balanced
```

This installs the skills, least-privilege agents, the enforcement shim,
a permission profile, AGENTS.md invariants, and a workspace contract.
Verify with `gravitas doctor`. Profiles: `fast`, `balanced`, `strict`.

## Verify it works

```bash
gravitas doctor                                   # checkout/installed/project scopes
gravitas decide --signals '{"trivial": true}'     # policy record
gravitas validators --root . --depth targeted    # discovered validators
```

Next: `docs/concepts.md` for the model, `docs/hosts.md` for host differences.
