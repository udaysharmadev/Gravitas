# ADR-0009: CLI surface completion

Date: 2026-10-07 · Status: accepted

## Context

`gravitas explain/migrate/update` were named in the UX plan but missing;
`init` required an explicit host; `doctor` said nothing about project
scaffolding; CI never proved the wheel outside the checkout.

## Decisions

1. `init` auto-detects hosts from project markers (opencode.json /
   .opencode, .agents / AGENTS.md), defaulting to opencode when nothing
   matches. Discovered validators are reported, never auto-bound to
   criteria (binding is a task decision).
2. `explain` renders session state + evidence deficit as text (default)
   or JSON; `migrate` normalizes legacy mode aliases and reports
   contract issues without failing; `update` is informational and
   offline-tolerant (exit 0 either way).
3. `doctor` gains informational project keys (adapters, workspace
   contract, installed skill); the required set stays runtime-only so
   project state can never fail an install check.
4. CI builds wheel+sdist via `build`, force-reinstalls the wheel, and
   smokes `doctor` + `decide` + `gravitas_init` import from outside any
   checkout. No command was added without implementation and tests.
