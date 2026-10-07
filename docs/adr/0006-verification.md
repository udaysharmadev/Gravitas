# ADR-0006: Repository-aware verification and evidence states

Date: 2026-10-07 · Status: accepted

## Context

Validators were contract-declared only (no discovery), language-stereotype
command chains were hard-coded in two skill scripts, coverage knew only
PASS/PENDING, and pre-mutation evidence could satisfy the finish gate.
No reproduction protocol or adversarial mode existed.

## Decisions

1. `gravitas_verify.discover_validators` builds a catalog from project
   config + resolvable binaries with provenance; nothing assumed from
   language. Empty catalog is reported, never padded. Skill scripts
   `verify.py`/`detect_project.py` delegate to it (stereotype chains kept
   only as labeled last-resort fallback).
2. Escalation (targeted/impact/suite/full) expands on depth, failure
   evidence, or release context -- never blindly. `gravitas validators`
   prints catalog + plan.
3. Per-criterion states PENDING/SUPPORTED/PASS/FAIL/BLOCKED/UNVERIFIABLE
   (`gravitas_evidence`); only fresh owned PASS gates. Freshness =
   evidence timestamp strictly after the latest ledger write (global,
   conservative; per-file attribution deferred). Latest fresh owned
   verdict governs, so a FAIL after a PASS blocks.
4. `repro_runner` + `gravitas repro` implement fail-before/pass-after
   pairs bound to criteria; `--unreproducible` records UNVERIFIABLE with
   reason and blocks the gate until contract amendment. Reproducer output
   is secret-redacted and schema-validated.
5. `expand_cases` + `gravitas edge-cases` generate deterministic boundary
   variants from seeds for execution through trusted project validators.
   Triggered selectively (strict/security/repeated-repair); never a claim
   of correctness by itself.

## Verification

99 unit tests OK (23 new: discovery incl. negative cases, escalation
rungs, state machine incl. staleness, repro pairs, schema validation);
full CI-equivalent gate green.
