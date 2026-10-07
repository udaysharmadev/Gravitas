# GRAVITAS — Repository Guide for Agents

Model-agnostic reliability runtime for coding agents. Invariants live in
`skills/gravitas/SKILL.md`; enforcement lives in `plugins/gravitas-antigravity/scripts/`.

## Kernel (always true)

1. Read target + tests + callers before editing.
2. Writes stay inside declared scope (`gravitas guard` / hooks deny the rest).
3. Completion needs fresh Gravitas-owned validator evidence (stale evidence blocks).
4. Never exact-retry a failure; change diagnosis, context, or strategy.
5. Contract criteria + required validators gate completion.
6. Mark unverifiable claims explicitly.

Planning is conditional: `gravitas decide --signals '{...}'` →
direct / compact / deep / replan with reason codes. No universal ceremony.

## Layout

```
├── skills/gravitas/               # Portable skill (kernel + references + resources)
├── skills/gravitas-highstakes/    # High-stakes checkpoint skill
├── plugins/gravitas-antigravity/  # Native runtime: scripts/, rules/, agents/, hooks.json
├── adapters/opencode/             # OpenCode agents, plugin shim, permission profiles
├── schemas/                       # contract.json, evidence.schema.json, episode.schema.json
├── benchmarks/                    # GravitasBench runner, manifest.yaml, cli.py
├── eval/tasks/                    # 30+ task specs (registry)
├── tests/                         # unittest suite (run: python -m unittest discover -s tests)
├── docs/adr/                      # Architecture decision records (read these first)
├── dist/gravitas-antigravity/     # Generated bundle (scripts/build-native-bundle.sh; do not hand-edit)
├── gravitas_cli.py / gravitas_init.py  # `gravitas` console script
```

## Commands

- `gravitas doctor` — runtime/project checks (checkout, installed, project scopes)
- `gravitas init [--host auto|opencode|antigravity]` — scaffold host config
- `gravitas decide/validators/context/summarize/explain` — policy, retrieval, state
- `gravitas validator/repro` — owned evidence execution
- `gravitas bench ...` — benchmark plumbing (synthetic fixtures; not publishable evidence)
- `gravitas migrate/gc/verify` — maintenance

## Verification

Run before claiming done: `python -m unittest discover -s tests`
(venv: `.venv/bin/python`). CI equivalent adds audit, validate, compile,
doctor, skill structure, bundle drift, and claims checks.

## Docs

- `docs/quickstart.md`, `docs/concepts.md`, `docs/hosts.md`, `docs/configuration.md`
- `docs/benchmark.md` (methodology + honesty gates), `docs/troubleshooting.md`
- `docs/contributing.md` (architecture + test expectations), `SECURITY.md` (enforcement limits)
- `docs/adr/` — why things are the way they are
