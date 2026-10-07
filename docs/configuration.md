# Configuration

## Effort profiles

| Profile | Planning | Delegation | Verification |
|---|---|---|---|
| `fast` | direct-first | none unless blocked | targeted only |
| `balanced` (default) | adaptive | conditional | targeted + affected |
| `strict` | deep-first + adversarial cases | conditional verifier | broader + independent check |

`fast` never bypasses scope or evidence gates. `strict` never runs
everything blindly — depth follows blast radius and uncertainty.

## OpenCode permission profiles

`gravitas init --host opencode --profile <name>` merges a profile into
`opencode.json` without clobbering existing keys:

- `fast`: edits allowed; shell allowed except destructive denies.
- `balanced`: shell asks by default; status/diff/log/grep allowed; destructive denied.
- `strict`: ask-by-default; reads/globs/grep/skills allowed; destructive denied.

## Contracts

Per-task `contract.json` (Antigravity sessions) or
`.gravitas/opencode-contract.json` (OpenCode workspace): `mode`,
`allowed_write_scope`, `acceptance_criteria`, `validators`, optional
`policy` dimensions. Legacy `plan-only`/`review-only` modes are accepted
as aliases (`gravitas migrate` normalizes them).

## Overrides

- Agent skills load on demand; `gravitas-highstakes` for migrations,
  deletions, auth, production config.
- Custom OpenCode agents live in `.opencode/agents/` with their own
  `permission` blocks; they do not inherit parent restrictions unless
  the host guarantees it.
