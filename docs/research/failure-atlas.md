# Gravitas Failure Atlas

Companion to `docs/research/gravitas-next-generation.md`. Every entry is sourced
from code and tests observed in this checkout (HEAD `9fe0839`). Status labels:
**protected** (covered by code + regression test), **partial** (covered on one
host or bypassable), **open** (no mitigation).

## F1 — Read-before-write bypass on OpenCode — PARTIAL (this session: shim records reads, guard enforces)
- Trigger: edit an existing file on OpenCode without a prior read.
- Before: `gravitas_cli.py cmd_guard` passed `reads=set()` always, so every
  existing-file edit denied (fail-closed but unusable) — or operators disabled
  the check. Antigravity path (`pre_tool.py:57-73` + `post_tool.py:112-121`)
  was protected.
- Fix: `adapters/opencode/plugin/gravitas.js` appends `{session, file}` rows to
  `.gravitas/opencode-reads.jsonl` on `tool.execute.after` only when the read
  succeeded and a session id is present; `cmd_guard` loads rows by exact
  `conversation_id` match (`_load_opencode_reads`). Recording in `before`
  would authorize writes for reads that then fail, and empty-session rows no
  longer satisfy named sessions.
- Tests: `tests/test_opencode.py` read-then-allow, cross-session deny, corrupt-line skip,
  empty-session deny, same-session allow, after-hook success-only recording.
- Residual: shell-redirect reads still invisible; see F5.

## F2 — Contradictory episodes entered reports — PROTECTED (this session)
- Trigger: `functional_solve:true` + validator `FAIL` in an episode JSON.
- Before: `benchmarks/cli.py cmd_report` called `validate_episodes(dir)` with no
  schema (`validate.py:38` → `[]`), so contradictions aggregated as FSR 1.0.
  Tracked as issue #27.
- Fix: `validate_episodes` requires `schema` (raises); `cmd_report` loads
  `schemas/episode.schema.json` with `Draft7Validator`, rejects contradictions
  and empty datasets (exit 1).
- Tests: `test_report_rejects_contradictory_episode`,
  `test_report_rejects_empty_episodes`, `test_validate_episodes_requires_schema`.

## F3 — Aggregate artifacts poison compare/metrics — PROTECTED (this session)
- Trigger: stored aggregate array (`[...].json`) inside episodes dir.
- Before: `compare.py main` globbed raw JSON and crashed/mis-paired on lists;
  `metrics.aggregate` raised `KeyError` on missing `configuration`.
- Fix: `valid_pairs` + `compare.main` skip non-dict payloads; `aggregate` skips
  rows without `configuration`.
- Test: `test_compare_skips_aggregate_artifacts`.

## F4 — Empty report renders success — PROTECTED (this session)
- Trigger: `report --episodes <empty dir>` exited 0 with an empty table.
- Fix: `cmd_report` returns 1 with `Episode validation failed: no valid episodes`.
- Test: `test_report_rejects_empty_episodes`.

## F5 — Shell side effects escape scope/read tracking — OPEN
- Evidence: `gravitas_policy.py:102-112` only checks enumerable redirect paths;
  TOCTOU explicitly out of scope; `post_tool.py:157-168` records only classified
  shell writes. Shell-redirect writes do not invalidate validator freshness
  unless classified.
- Oracle: fixture that writes via `python -c "open(...).write(...)"` then claims
  fresh PASS should be caught or documented as OS-sandbox territory.

## F6 — Reproducer identity weaker than validator — OPEN
- Evidence: `validator_runner.py:66-95` binds argv to contract criteria;
  `repro_runner.py:84-85` binds criterion IDs only. Swapped reproducer commands
  are not detected at the gate.
- Oracle: run two reproducers with swapped commands; gate must reject.

## F7 — Full-ledger rewrite undetected — OPEN
- Evidence: `evidence_chain.verify_chain` detects tampering within a chain
  (`test_v5_hardening.py:195-210`); full rewrite with fresh hashes is not
  anchored anywhere (`docs/audits/v5-audit.md:86`).
- Direction: external anchor (signed checkpoint) — research-only, do not
  over-claim containment.

## F8 — Stale-context resume without mandatory re-verify — OPEN
- Evidence: `resolve-failure` clears fingerprint bans (`pre_tool.py:121-124`);
  nothing forces target re-read or fresh validator run after arm.
- Direction: require re-read + fresh owned-validator PASS for the touched
  criteria before the same fingerprint can gate completion.

## F9 — Recovery doc contradicts enforcement — OPEN (doc fix pending)
- Evidence: `skills/gravitas/references/recovery.md:40,50-51` ("do NOT re-read")
  vs `pre_tool` + `evaluate_action:119-125` read-before-write deny and
  `docs/edge-cases.md:16` (re-read before every mutation).
- Direction: scope the no-re-read rule to unchanged files; mandate hash-checked
  re-read after interruption, model change, or external modification.

## F10 — Cumulative-effect / context-loss patterns unmitigated — OPEN
- Evidence: `docs/failure-modes.md:178-230` (FM-11 escalation chains,
  FM-12 self-conditioning, FM-14 context loss) have no detector; trace analyzer
  (System 9) not yet built.
- Direction: bounded deterministic trace linter over `evidence.jsonl` +
  `failures.jsonl` (repeat-action, thrash, stale-evidence patterns).
