# Gravitas OpenCode Adapter

First-class OpenCode support via native surfaces: AGENTS.md invariants,
Agent Skills, custom agents, `permission` configuration, and a JS plugin
shim (`tool.execute.before`) backed by the same Python policy engine as
Antigravity. Installed and verified against OpenCode 1.18.x (`permission`
schema). OpenCode v2 uses a different `permissions`-array schema; see
"Capability differences".

## What `gravitas init --host opencode` installs

- `.agents/skills/gravitas/` + `gravitas-highstakes/` (shared with Antigravity discovery)
- `.opencode/agents/{investigator,reviewer,impact-auditor,test-adversary}.md`
- `.opencode/plugins/gravitas.js` (enforcement shim)
- `opencode.json` permission profile (merged, never clobbered; unparseable
  configs and `opencode.jsonc`-only projects are left untouched with a
  `warnings` entry for manual merge)
- `AGENTS.md` invariant block (idempotent markers)
- `.gravitas/opencode-contract.json` (workspace contract for the shim)

## Capability differences (honest)

- OpenCode has `tool.execute.before` (block by throwing) and an
  after-completion hook, but no Stop-gate equivalent. Completion gating runs
  manually via `gravitas summarize` + validator evidence, not automatic denial.
- `force_ask` resolves to hard deny in the shim (no ask channel).
- Validator evidence remains manual (`gravitas validator`, `gravitas repro`);
  completion events only dirty freshness and never count as PASS evidence.
  Successful `edit`, `write`, `patch`, and mutating `bash` completions are
  recorded in `.gravitas/opencode-completions.jsonl` with their OpenCode
  session ID. Failed reads are not recorded as successful completion events.
- To include those mutations in freshness checks, bind validator evidence to
  `.gravitas/sessions/opencode-<sha256(session-id)>/` using the exact session
  ID from OpenCode. The guard reports stale criterion IDs; completion events
  never repair or satisfy evidence.
- The shim shells to `gravitas guard` (python3 required). If unreachable,
  mutating calls are denied; run `gravitas doctor`.
- The workspace contract is shared, while completion evidence is filtered by
  the exact OpenCode conversation/session ID.
