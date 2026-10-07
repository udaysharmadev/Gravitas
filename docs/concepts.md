# Concepts

## Contract

A machine-readable task declaration (`contract.json`): mode, objective,
acceptance criteria, `allowed_write_scope`, validators, and optional
policy dimensions (`schemas/contract.json`). The contract gates action
policy and completion. Amend it instead of routing around it.

## Policy

`gravitas decide --signals '{...}'` emits
`{planning, context_depth, verification_depth, delegation, reason_codes}`.
Levels: `direct` (trivial/localized), `compact` (dependent changes),
`deep` (architecture/security/migration/fanout), `replan` (evidence
invalidated assumptions). Risk and effort are independent dimensions;
explicit rules now, calibration from benchmark data later.

## Context

The Context Engine builds a cached repository graph (symbols, imports,
callers, tests, configs, co-change) and returns relevance-ranked,
depth-bounded file sets (`target` → `dependency` → `subsystem`).
Deterministic first; no vector database, no whole-repo dumps.

## Evidence

Every criterion is PENDING, SUPPORTED, PASS, FAIL, BLOCKED, or
UNVERIFIABLE. Only **fresh** Gravitas-owned validator evidence (timestamp
after the final mutation) satisfies the finish gate. Generic test output
and self-review never count. `gravitas summarize` shows the matrix;
`gravitas explain` narrates the deficit.

## Action policy

Normalized actions carry capability levels (`none/write/mutation/
destructive`). Read-only modes deny writes and non-query execution;
out-of-scope writes are denied including enumerable shell writes;
destructive operations require confirmation. Hooks are advisory policy,
not a sandbox — see `SECURITY.md`.

## Verification

Validator discovery (project config + binaries, never language
stereotypes) feeds escalation: targeted → impact → suite → full.
Reproduction-first debugging (`gravitas repro --phase before/after`);
deterministic edge-case expansion for strict/security work.

## Recovery

Append-only evidence/failure ledgers rebuild durable state: objective,
criteria, scope, decisions, failed approaches with causes, validators,
risks, next action (`gravitas summarize`, `resume_session.py`).
