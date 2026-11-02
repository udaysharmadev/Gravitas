# GRAVITAS V5 Audit — Baseline 8a078dd011ae75b12dc319b6862d6124d385bf8e (branch v5-audit-hardening)

Date: 2026-10-15. Host: opencode v2.0.28, agy 1.2.2, python 3.14.6 (.venv). Baseline suite: 164 tests OK.
Prior fixes verified present: PR #1 (shell injection), PR #2 squash 297a613 (unparseable config preserve), PR #3 squash 5874c03 (newline separator), jsonc-only handling d7c82cd. No reintroduction.

## Severity-ranked findings (all reproduced, temp dirs only)

### P0 — enforcement bypass
- P0-1 `adapters/opencode/plugin/gravitas.js:74-75` wrong hook arity `(input)`; real API is `(input, output)` with args in `output.args`. Extraction always `{}` → `CommandLine:""`, `TargetFile:""` → guard allows; correct envelope denies. Repro: node toEnvelope with real shape → allow vs deny.
- P0-2 `gravitas.js:58-70` + `gravitas_cli.py:272-280` fail-open: shim catch-all → allow; guard ModuleNotFoundError → allow. Repro: isolated dir guard → allow; ENOENT/timeout → allow.
- P0-3 `gravitas_action.py:114,185-187` `git branch -D/-d` → none (read-only). Must be destructive.
- P0-4 `gravitas_action.py:224` `find -execdir` (also -ok/-okdir) → none. Must be destructive.
- P0-5 `gravitas_action.py:200-212` `python3 -` (stdin) → none. Must be mutation.
- P0-6 wrappers (`env`, `sudo`, `VAR=`…) mask inner destructive as mutation/unknown. Must strip and re-dispatch.

### P1 — unsafe defaults / stale trust
- P1-1 `gravitas_cli.py:298-304` missing/corrupt contract → `{}` → implement + empty scope → allow. Must deny mutating or warn explicitly.
- P1-2 `gravitas_policy.py:37-41` invalid mode → implement (most permissive). Guard must reject unknown mode fail-closed.
- P1-3 `post_invocation.py:57-71` completed_criteria seeded and only extended; stale PASS retained. Must recompute from fresh owned PASS.
- P1-4 `stop_gate.py:121-130` circuit breaker returns continue forever → livelock. Must terminate safely without false PASS.
- P1-5 `stop_gate.py` never calls `verify_chain`; tampered ledger still gates allow. Must verify before gate.
- P1-6 `validator_runner.py:89` (+repro) no timeout, unbounded capture; `git_snapshot` no timeout. Must bound.
- P1-7 `gravitas.js` vs `gravitas_cli.py:259` glob mapping divergence (list_dir vs find_by_name). Must unify.
- P1-8 `sh -c`/`xargs` inner destructive masked as mutation. Must recurse/max.
- P1-9 `git stash drop/clear`, `worktree remove` → mutation not destructive; `git -C` scope escape + over-block. Must fix.
- P1-10 `gravitas_init.py:96-113` profile validated after copies → partial scaffold on failure. Must preflight.
- P1-11 `pyproject.toml:22-38` wheel omits `skills/gravitas-highstakes`, `SESSION_FAILURES.md`, `rules/`; doctor blind. Must ship + check.
- P1-12 9 hook scripts lack `from __future__ import annotations` → crash on py3.9 despite `>=3.9` claim. Must add import + CI matrix.

### P2 — docs/process
- P2-1 `hooks/hooks.json` dead duplicate. Remove/guard.
- P2-2 `dist/` tracked + `cp -R` nondeterministic; CI bare `git diff`. Manifest or untrack (deferred: keep tracked + drift check this round).
- P2-3 CI checkout v3/v4 mix, single py3.12, unpinned deps, narrow py_compile. Harden.
- P2-4 SKILL 6 invariants vs GEMINI/CLAUDE 5 rules + Tier language. Reconcile to canonical 6.
- P2-5 `benchmarks/runner/audit.py` skips `contract.json`, `benchmark_output.json`. Extend glob.
- P2-6 doctor missing post_tool/post_invocation/highstakes/rules/schemas checks. Extend.
- P2-7 quoted separators split inside quotes (fail-closed noisy). Document; quote-aware split deferred.

## Remediation plan
1. P0 shim+guard fail-closed, classifier destructive fixes, wrappers, contract/mode safe defaults. (this session)
2. Evidence: recompute completed, verify chain in gate, safe termination, validator bounds. (this session)
3. Packaging: wheel assets, init preflight, doctor, py3.9 imports, audit glob, CI. (this session)
4. Docs: 6-invariant reconciliation, compatibility matrix (OpenCode V1 unverified / V2 smoke; Antigravity agy validate where available). (this session)
5. Deferred: quote-aware shell split, dist untracking, full benchmark methodology, perf caching — recorded in continuation section below.

## Continuation (if budget exhausts)
- Completed vs pending listed in final summary. All P0 targeted above; P2-2/P2-7 deferred explicitly.

---

# V5 Implementation record (branch v5-audit-hardening)

## Implemented (verified this session)
- A1 shim: `(input, output)` arity, fail-closed deny on unreachable/unparseable/unknown verdict, local deny on missing mutating args or tool, glob→find_by_name aligned with guard. Tests: ShimHookTests (4).
- A2 guard: import failure → deny; contract states active/unconfigured/degraded in output; missing/corrupt/non-object contract denies mutating, allows read with warning; unknown mode denies; empty mutating args deny; unknown tools allow with warning. Tests: GuardPolicyStateTests (5).
- A3 classifier: git branch -D/-d/-m destructive; stash drop/clear destructive; worktree remove destructive / list none; git -C/-c/--git-dir/--work-tree stripped + dirs into paths; find -execdir/-ok/-okdir/-fls destructive; python/node `-`/bare REPL mutation with --version allowlist; env/sudo/VAR= wrappers stripped; sh -c and xargs recursive max (depth-capped). Tests: ClassifierV5Tests (21-case table + scope test). Existing BYPASS_CORPUS minimums still hold.
- A4/A5 evidence: stop_gate verifies chain before gate (tamper → continue); post_invocation recomputes completed from fresh owned PASS (stale pruned). Tests: tamper-blocks-gate, stale-not-retained.
- A6 gate: unparseable payload → continue; 3+ cycles → allow + unverified:true + deficit (safe termination, never false PASS). Updated test_runtime expectation.
- A7 runners: --timeout (default 300s), file-backed capped output (1MB), TIMEOUT FAIL evidence + rc 124, git_snapshot 10s timeout. Tests: timeout-records-fail. Schema extended with `timed_out`.
- D1/D2 packaging: wheel ships highstakes + SESSION_FAILURES + rules (verified in built wheel + isolated-venv init installs both skills); _copy_tree missing-source no-op; init_opencode preflights profile/templates before mutation, bad profile leaves empty dir + stable schema. Tests: InitV5 + PackagingV5.
- P1-12 py3.9: `from __future__ import annotations` in 9 hook scripts; CI matrix 3.9/3.12; extended py_compile; checkout v4 + setup-python pin in verify-skill.
- Docs: GEMINI/CLAUDE reconciled to canonical 6 invariants + decide record; hosts.md compatibility matrix (see below); audit.py checks all schemas/*.json + rejects legacy hooks/hooks.json (deleted, `agy plugin validate` still RC 0 on canonical + dist).
- test_packaging extended to new assets.

## Compatibility matrix
| Host | Status |
|---|---|
| Antigravity Native (`agy plugin validate` 1.2.2) | VALIDATED: canonical + dist bundles RC 0 |
| OpenCode v2.0.28 (installed) | PARTIAL: shim `(input,output)` signature + fail-closed verified by contract tests + node repro; no live `opencode` tool-run observed — not claimed as live-verified |
| OpenCode V1 | UNVALIDATED: permission profiles ship; V1 runtime not installed here |
| Python | 3.12 suite green; 3.9 via future-imports + CI matrix (no 3.9 interpreter on this host — matrix covers) |

## Verification results (observed)
- `.venv/bin/python -m unittest discover -s tests`: Ran 182 tests OK (baseline 164 + 18 new)
- `benchmarks/runner/audit.py`: Audit PASS
- `benchmarks/runner/validate.py --episodes benchmarks/results --allow-empty`: 0 validated, 2 skipped, 0 failed
- `py_compile` (cli+init+scripts+skills+runner): clean
- `.github/scripts/validate_skill.py`: PASS; `scripts/check_readme_claims.py`: PASS
- `bash scripts/build-native-bundle.sh` + `git diff` review: dist matches canonical (diff shown, committed here)
- Isolated venv wheel install: `gravitas doctor` mode=installed RC 0, `gravitas init --host opencode` installs both skills + opencode.json
- `agy plugin validate` canonical + dist: ok, RC 0
- No model quota spent; no comparative benchmark claims made.

## Remaining limitations (honest)
- Shell classifier is not filesystem containment; quoted-separator splitting is regex-based (fail-closed noisy, e.g. `echo "a;b"` → mutation); heredoc bodies mis-split safe-side. OS/host isolation still required for true containment.
- User-local anchors detect project-ledger rewrites only while the anchor directory remains outside the attacker-controlled write scope; they do not resist a same-user process that can rewrite both locations.
- Scope gating covers enumerable paths only; TOCTOU races documented in policy.
- Opencode read-before-write ledger is per-call (`reads=set()`); existing-file writes via shim deny until session read-tracking exists — surfaced as explicit reason.
- No breaking changes; no version bump; "V5" remains upgrade direction, not a release designation.

## Safety notes
- No `rm -rf`, `git reset --hard`, force push, cloud changes, or home-directory benchmark runs. All dangerous inputs tested as data in temp dirs. Branch `v5-audit-hardening` local only; merge/push requires explicit authorization.

---

# V5 round-2 record (same branch)

## Implemented
- C1 `decide()`: high-stakes flags (destructive/security/auth/migration/broad_fanout) now override the trivial/read_only fast-path (`{trivial,destructive}` → deep, was direct); all count signals coerced via `_safe_int` (garbage strings → defaults, no traceback). Plain trivial/read_only still direct. Tests: DecideBorderlineTests.
- C3 recovery: `pre_tool` honors `resolved:true` markers (aligned with stop_gate/post_invocation/resume); new `gravitas resolve-failure --session-dir … --fingerprint … --reason … --file … [--criterion-id …]` appends a marker, keeping the original record. Previously the exact-fingerprint ban was permanent with no recovery path. Tests: ban → resolve → allow; unresolved still bans.
- C2 measured, no change: `build_index` 200-file synthetic repo 0.22s, this repo (102 files) 0.53s; refresh/drop/add covered by existing RepoGraphTests. No caching added (correctness over marginal speed).
- C4 verified, no change: coordinator retired to conditional delegation; agent roles conditional with quota justification; no host claims native subagents falsely (OpenCode agent frontmatter uses host `mode: subagent`, fixture-pinned).
- C5 verified, no change: conversation isolation pinned by existing test; sessions are separate directories by construction.
- D4 `SHA256SUMS` content manifest in build script (sorted, deterministic across rebuilds) + CI asserts its presence; `git diff --exit-code` drift check retained.
- E2 SkillReferenceTests: every `references|resources/*.md` linked from SKILL.md exists on disk and ships in the wheel manifest.
- B1-live: official plugin docs confirm `.opencode/plugins/` auto-load + `(input, output)` hook shape verbatim; live model-backed run NOT performed (paid quota, needs budget authorization) — recorded as blocked, not claimed.
- F4 measured: hook invocation ~15ms median (python startup bound), index 0.5s one-time + cached refresh. No bottlenecks warranting correctness-risky caching.
- G1/G2 verified, no change: fast/balanced/strict profiles differ meaningfully (existing profile tests); guard/shim failures emit what/which/remediation.

## Verification (round 2, observed)
- Full suite: 188 tests OK (182 + 6 new)
- Rebuild ×2: SHA256SUMS stable; `git diff --exit-code -- dist` clean after commit
- `agy plugin validate` still RC 0 (canonical + dist) — rerun at final gate
