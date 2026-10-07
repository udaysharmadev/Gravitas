# ADR-0004: Normalized action/policy models and kernel shrink

Date: 2026-10-07 · Status: accepted

## Context

Policy logic was scattered across Antigravity tool-name checks in
`pre_tool.py`/`post_tool.py`, shell intent was a regex denylist, and three
mode vocabularies disagreed (schema, hook, skill). SKILL.md mixed kernel
invariants with procedures.

## Decisions

1. Core policy consumes a normalized `Action`
   (kind/tool/paths/executable/argv/mutation/host-metadata), never host
   tool names. `antigravity_envelope()` is the Antigravity adapter; the
   `HostEnvelope` interface is host-agnostic for the OpenCode adapter.
2. Shell classification is tokenizer-based (shlex + operator scan) with
   capability levels none/write/mutation/destructive. Unparsable input
   fails closed. `mv` classifies destructive (destroys the source path);
   `drop table` in read-only modes now denies instead of asking.
3. Unified mode vocabulary (8 modes, 5 read-only); `plan-only`/`review-only`
   accepted as aliases, schema widened additively, contract gains an
   optional `policy` dimensions object. Absent dimensions mean unknown.
4. `decide()` emits planning/context/verification/delegation + reason codes
   from explicit rules (no weights); exposed as `gravitas decide`.
   Delegation defaults to none; investigator/reviewer/impact-auditor only on
   explicit signals.
5. SKILL.md shrunk 259 -> ~185 lines: 6 invariants, policy record, modes,
   decision records, evidence hierarchy, effort profiles, delegation.
   Tier language remains in agent files with a compat mapping until
   migration. Shell scope enforcement for non-tool writes stays a known
   gap for the action-policy phase.

## Verification

64 unit tests OK (100-case action-lock corpus + 40-case bypass corpus +
policy-record matrix); full CI-equivalent gate green.
