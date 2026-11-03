# GRAVITAS production-readiness gates

Last reviewed: **2026-11-03**. This board distinguishes locally verified
properties from release readiness. The broader source-linked assessment is
[the project review](project-review-2026-11-03.md). The subsequent
[pre-push validation](prepush-validation-2026-11-03.md) repairs contributor
workflow orchestration, user-install lookup, and native agent metadata.

| Gate | Status | Evidence / remaining boundary |
|---|---|---|
| Agent Skills format | TESTED | Frontmatter and portable skill structure have deterministic validators. Format conformance is not runtime enforcement. |
| Core project scaffolding | TESTED | Non-clobbering/idempotent init paths pass unit tests and clean installed external-workspace checks for both hosts. |
| Native generated bundle | TESTED | Canonical-source and deterministic SHA-256 manifest parity checks pass; strict agy 1.4.9 loads 2 skills and 3 agents without warnings. |
| Runtime evidence reduction | TESTED | Latest required-validator failures block completion; assigned coverage and saved recovery state share the reducer. |
| Full host lifecycle | PARTIAL | Local hook fixtures are tested; enclosing-validator self-staleness remains a known separate issue. No new live model trajectory was executed. |
| OpenCode adapter | PARTIAL | Guard, scope, and session-read logic have tests; after-hook payload/version mismatch remains. No automatic native-equivalent Stop hook. |
| Delegated child handoff | PARTIAL | Happy paths are tested; empty mutating scope, caller-selected handoff criteria, and child evidence authentication need hardening. |
| Wheel/sdist installation | TESTED / PARTIAL | Fresh-venv and actual disposable user installs pass installed-mode and external-workspace init checks. Cross-platform installation coverage remains incomplete. |
| Python/platform support | PARTIAL | Package preserves Python >=3.9; CI covers Ubuntu 3.9/3.12/3.14 with Node 22. Local full suites passed on macOS/Python 3.12.13 and 3.14.6. Python 3.9 is upstream end-of-life; Windows/live-host certification is not established here. |
| Benchmark outcome integrity | TESTED | Failed checkpoints/additional mandatory validators prevent a solve; contradictory component values and duplicate criteria are rejected. |
| Benchmark corpus | PARTIAL | 48 registered specs, 10 lanes, three holdouts; executable factory still rotates five synthetic exercises. HARV specifications are not real-repository runner integration. |
| Publication eligibility | TESTED | Explicit repository provenance, paired revision consistency, uniqueness, and >=30 tasks x >=5 valid paired runs are required. The gate checks declarations, not artifact authenticity. |
| Comparative results | BLOCKED | No eligible licensed repository experiment or published paired dataset is established. |
| Measured performance claims | BLOCKED | No model gains, cost reduction, or competitor superiority were measured by this upgrade. |

## Verification boundaries

The pre-upgrade local suite reported `Ran 391 tests in 19.666s` and `OK`.
The integrity regressions add actual local subprocess lifecycles and
provider-mocked benchmark cases; run the suite for the current total:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests
.venv/bin/python benchmarks/runner/audit.py
.venv/bin/python .github/scripts/validate_skill.py
.venv/bin/python scripts/check_readme_claims.py
```

Passing local tests does not certify an untested host version, a secure
sandbox, or a statistically valid model comparison. Native bundle/source
parity is checked by `tests/test_bundle_manifest.py`. Tests create temporary
local repositories/files and mock provider calls; no paid inference is
needed.

## Release blockers

1. Complete host payload/lifecycle tests and repair the documented validator,
   OpenCode after-hook, and child-handoff boundaries.
2. Verify clean installed CLI behavior across declared installation schemes
   and supported Python/OS versions.
3. Execute real licensed pinned tasks with independently held executable
   validators, retained artifacts, and reproducible configurations.
4. Collect the pre-registered paired study, account for task clustering, and
   review provenance/uncertainty before publishing performance numbers.

The older 2026-10-07 readiness assertions are historical observations, not
current blanket certification. The 2026-11-03 review deliberately downgrades
areas where tests or documentation did not support the broader claim.
