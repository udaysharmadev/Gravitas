# ADR-0003: Layered reliability runtime direction

Date: 2026-10-07 · Status: proposed (phases 2+)

## Context

GRAVITAS is currently rule-heavy prompt prose plus a thin hook layer. Prompt
rules do not enforce; hooks do not understand policy. The system must grow
into a runtime without becoming twelve giant abstractions.

## Decisions

1. Shrink the always-on kernel to machine-checkable invariants (grounding
   before mutation, scope enforcement, evidence-backed completion, no exact
   retry of failed approaches, contract satisfaction). Procedures move to
   progressive-disclosure skills.
2. Split risk from effort: policy dimensions (action risk, reversibility,
   uncertainty, blast radius, verification depth) instead of one tier
   number; explicit rules first, calibration from GravitasBench data later.
3. Planning becomes conditional (direct / compact / deep / replan) with a
   machine-readable policy record; no universal "2+ files means full plan".
4. Context, verification, evidence, recovery, delegation, and host adapters
   evolve as small interfaces with tests, in dependency order (phases 2-8).
   Every mechanism needs a failure mode, an observable output, and a reason
   it lives in runtime rather than prose.
5. Current `pre_tool.py` regex classification is treated as insufficient
   until adversarial tests prove otherwise (threat model recorded for the
   action-policy phase). Plan-only modes claim no sandbox guarantee the host
   cannot enforce.

## Deferred

Host payload research (current Antigravity schemas, OpenCode adapter
surfaces) happens at the adapter phases, verified against live docs, not
copied from repository assumptions.
