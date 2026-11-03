# Pre-push workflow and installation validation — 2026-11-03

This follow-up checks the earlier [integrity upgrade](project-review-2026-11-03.md)
from workflow orchestration through installed-package behavior. It supersedes
that review's deferred contributor-sync and user-install findings, without
claiming the unrelated lifecycle or benchmark-provenance gaps are fixed.

## Confirmed issues and repairs

### Contributor synchronization

The workflow wrote `IN_SYNC` only to `$GITHUB_ENV`, then immediately read the
unset shell variable. Generation was skipped, and both generator/check errors
could be reported as success. It now runs the generator once, derives the
changed state from `git diff`, and propagates generator/Git/commit errors.

Offline workflow-shell tests cover unchanged files, changed files, generator
failure, and Git failure. They stub Python and Git: no contributor API calls,
PR creation, auto-merge, or remote synchronization was executed for validation.

### Verification coverage

`GRAVITAS Verify` now runs on feature-branch pushes, in addition to PRs and
manual dispatch. Verification workflows explicitly request read-only contents
permission. Node 22 is provisioned for adapter tests, and the Python matrix is
3.9, 3.12, and 3.14. Python 3.9 remains a compatibility floor, not an upstream
support recommendation; it is end-of-life.

The wheel smoke test uses a fresh virtual environment and installs dependencies,
rather than force-reinstalling into the interpreter already populated by the
checkout. `scripts/check_installed_package.py` runs in external temporary
projects and checks installed mode, the console entry point, doctor, planning,
OpenCode/Antigravity initialization, configuration preservation, and idempotence.

### User installation

An actual disposable `pip --user` installation reproduced the unresolved
runtime path. The CLI now matches its imported module directory to a user
installation scheme before loading that scheme's `share/gravitas` assets.
A user-installed module does not silently borrow unrelated prefix assets.
Prefix/virtual-environment behavior is preserved.

The repaired wheel passed the same external-project checker in both a fresh
virtual environment and a disposable user base. Nothing was installed into the
user's real global or user package directories.

### Native agent loading

`agy plugin validate --strict` exposed three ignored agent files lacking
`name`/`description` frontmatter. Metadata was added without changing the agents'
behavior, and the generated bundle was rebuilt. The strict validator now loads
**2 skills, 3 agents, 1 rule, and the hook configuration** with no warnings.
It notes only the optional missing logo. This validates packaging, not a live
model trajectory.

## Executed local checks

- Full unittest discovery passed **463 tests** on Python **3.14.6** and on a
  clean Python **3.12.13** environment. The pre-follow-up baseline was 446;
  this batch adds 17 workflow, installation-scheme, and agent-metadata tests.
- Actionlint **1.7.12** passed for all three workflows. Its official release
  archive was checked against the published SHA-256 checksum.
- Every inline workflow shell script passed `bash -n`; regression tests
  reject direct GitHub-expression interpolation into shell bodies.
- Wheel and source distribution built successfully in isolated source copies.
- Fresh-venv and disposable user-install smoke checks passed, including both
  host scaffolds, installed-mode detection, and non-clobbering repeat init.
- Strict Antigravity plugin validation passed on canonical sources and the
  rebuilt distribution using `agy` **1.4.9**.

The final pre-push gate also reruns audit, episode validation, calibration,
portable skill validation, public-claims checks, syntax/schema checks,
generated-bundle parity, diff hygiene, and contract-bound owned evidence.
Exact local logs and hashes are retained in the ignored session directory
`.gravitas/sessions/prepush-validation-20261103/`.

## GitHub expectations and limits

The authorized destination is `origin/ascension/phase-b-foundation`, not a
force push or direct merge to `main`. A push should start **Verify Skill** and
**GRAVITAS Verify** for the pushed commit, including all three Python matrix
jobs. Remote results must be checked against that exact commit; local success
or a green skill-only job is not a substitute.

The contributor workflow remains default-branch/schedule/manual-only. It is not
run as part of this feature-branch push. Bot PR and auto-merge behavior still
depends on repository settings and is not certified by offline tests.

No Codex CLI/API, live model benchmark, release publication, production
deployment, or repository-setting change was used. Remaining host validator
self-staleness, OpenCode payload-version compatibility, child-handoff integrity,
and real benchmark custody are still tracked in the project review.
