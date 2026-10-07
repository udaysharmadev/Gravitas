# ADR-0008: Host adapters (Antigravity modernization + OpenCode)

Date: 2026-10-07 · Status: accepted

## Context

The Antigravity adapter used September assumptions; OpenCode had no
support. Platform behavior was re-verified against live docs on 2026-10-07
(Antigravity plugin/rules/skills/hooks references, workflows-to-skills
migration guide, OpenCode 1.x skills/agents/permissions/plugins/rules
references) and against local installs (`agy` 1.2.2, OpenCode 1.18.35).

## Decisions

1. Antigravity: adapter reads `hookEventName` (not just legacy `hookEvent`);
   observed tool aliases (`edit_file`, `list_dir`+`DirectoryPath`) map onto
   the normalized model, fixture-pinned. Unknown tools stay visible and
   ungated. Plugin gains `rules/gravitas-invariants.md` (trigger:
   always_on) for the persistent kernel; procedures stay in skills,
   enforcement in hooks -- no duplicated giant policy.
2. `.agents/workflows/gravitas-highstakes.md` migrated to
   `skills/gravitas-highstakes/` (workflows stop executing 2026-10-19 per
   official docs). Canonical `skills/` ships both skills in the bundle;
   `agy plugin validate` passes (2 skills, 3 agents, hooks).
3. OpenCode (v1 `permission` schema, matching installed 1.18.x): AGENTS.md
   invariant block, shared `.agents/skills/` copies, four least-privilege
   custom agents, three permission profiles, and a JS shim on
   `tool.execute.before` backed by `gravitas guard` (same Python policy).
4. Honest deltas: no Stop-gate equivalent (manual `summarize`), force_ask
   becomes hard deny (no ask channel), shim enforces but does not record
   sessions, python3+`gravitas` required with allow-with-warning
   degradation, per-workspace (not per-conversation) contract.
5. `gravitas init --host` scaffolds without clobbering (JSON per-key merge,
   idempotent AGENTS.md markers, existing files skipped).

## Verification

143 unit tests OK (24 new: fixtures across payload versions, bundle
surfaces, init idempotence, guard mapping, shim mapping via node);
`agy plugin validate` exit 0; wheel contains init + adapter templates;
full CI-equivalent gate green.
