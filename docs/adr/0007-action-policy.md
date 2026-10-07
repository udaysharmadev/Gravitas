# ADR-0007: Action-policy hardening

Date: 2026-10-07 · Status: accepted

## Context

Shell classification missed whole tool classes (patch, editors,
archivers, rsync), enumerated no file operands, applied write scope only
to dedicated edit tools, allowed runner `--cwd` anywhere, and had no
fuzz coverage. SECURITY.md implied containment without stating limits.

## Decisions

1. Classifier extended (patch/editors/archivers/install/rsync/perl);
   `tee`/`dd` file operands extracted alongside redirect targets.
2. Enumerable shell writes obey `allowed_write_scope` in all modes.
   Non-enumerable side effects (test runners, interpreters) stay governed
   by capability level -- documented, not pretended otherwise.
3. Substitution is a mutation *floor*, not a verdict: outer segments still
   classify (found by fuzz: `curl $(id)` was under-classified).
4. Runner `--cwd` confined to the invoking workspace via realpath
   comparison (symlink-aware).
5. Sensitive reads flagged by whole-segment name matching (`tokenizer.py`
   must not match); ledger persistence redacted as before.
6. Deterministic seeded-grammar fuzzing (no new deps): 2,500 cases for
   crash-freedom, monotonic escalation, and redirect floor.
7. SECURITY.md rewritten as an explicit enforcement/limitation contract:
   hooks are advisory policy, not a sandbox. TOCTOU, host-bypass, and
   ledger-rewrite limits stated plainly.

## Verification

119 unit tests OK (20 new security tests); full CI-equivalent gate green.
