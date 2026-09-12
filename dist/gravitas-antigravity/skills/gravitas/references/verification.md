# Gravitas -- Verification Reference

## The Hierarchy

Prefer external, deterministic evidence over model self-assessment:
1. Compiler / type checker
2. Unit test runner (actual output)
3. Integration test runner
4. Static analysis (lint, security scan)
5. Deterministic validator
6. Diff inspection
7. Model self-review (supplementary only, lowest weight)

Model self-critique is not verification. It is a weak signal to use when better evidence is unavailable.

## Evidence Requirements by Claim

| Claim | Minimum Required Evidence |
|-------|------------------------|
| Tests pass | Pass count + total + 0 failures from actual run |
| Lint clean | Linter output with 0 warnings |
| Type-safe | tsc/mypy/pyright output clean |
| Build succeeds | Build output last line |
| No regressions | Before count vs after count, both shown |
| Fixed | Before behavior observed, after behavior observed |
| Requirement covered | Evidence entry in ledger linking criterion to proof |

## VERDICT Format

Every verification session ends with exactly one of:
VERDICT: PASS
or
VERDICT: FAIL -- [specific reason]
[failing output]

Never: VERDICT: PASS (with caveats) -- that is a FAIL.
Never: VERDICT: PARTIAL PASS -- that is a FAIL.

## Regression Baseline

Before any change:
1. Run full test suite, record exact count
2. Note existing lint warnings (do not introduce new ones)

After changes:
1. Run full test suite
2. After count >= before count -- not a regression
3. New lint warnings -- must fix before VERDICT: PASS

## Scope-Appropriate Verification

| Scope | Verification |
|-------|-------------|
| Single function change | Targeted: run tests for that module |
| Multi-file feature | Affected: run all tests for changed modules |
| Shared utility change | Broad: run full test suite |
| Auth/security/schema | Full: complete test suite + static analysis |

## When Self-Review Is Acceptable

Only as supplementary evidence when no test runner is available, the change is purely cosmetic, or the validator cannot run in current environment. State the limitation explicitly:
Note: test runner unavailable in this environment. Diff review only.
VERDICT: CONDITIONAL PASS -- requires human test execution before merge.

## Completion Gating

The Stop hook will not allow task completion until:
- All acceptance criteria have evidence entries in the ledger
- Required validators have been observed to run
- No known failures are unresolved
- The agent's completion claim is consistent with the evidence trace
