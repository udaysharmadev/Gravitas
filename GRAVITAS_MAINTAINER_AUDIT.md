# GRAVITAS Maintainer Audit — 2026-10-17 UTC

- Audit timestamp (UTC): 2026-10-17 (execution); snapshot re-verified live
- Latest `main` SHA: `58c0bf60558a188fbc576f3471c9ff355ce81c6` ("Pr 49 51 52 readme (#53)")
- Auth: `gh auth status` → logged in as `udaysharmadev` (keyring, scopes gist/read:org/repo/workflow); no tokens printed
- Inventory (live, matches 2026-10-18 snapshot): **23 issues (15 open, 8 closed)**, **30 PRs (13 open, 17 closed)**. No new items.
- Aggregate vehicles: #48 = `0e78b86` "Merge all prs"; #53 = `58c0bf6` (squash of branch incl. #49/#51/#52 content)
- Verification env: detached worktree at `origin/main` (`/tmp/gravitas-main-check`), project venv `.venv/bin/python`
- Full suite on main HEAD: `python -m unittest discover -s tests` → **250 tests, OK** (system python lacks jsonschema; venv required per AGENTS.md)
- Public CI on HEAD `58c0bf6`: GRAVITAS Verification Gate (3.9) success, (3.12) success, verify success
- Open PR heads: 10× CONFLICTING (#34,35,36,37,38,39,40,41,46,47,49), 2× MERGEABLE-but-duplicate (#51, #52)

## PR dispositions (all 13 open → close as superseded, no merge, no branch deletion)

| PR | Linked issue | Head | Live state | Evidence on main | Action |
|----|----|----|----|----|----|
| #34 | #11 | 6b001c9 CONFLICT; Gate 3.12 FAILURE | unspaced-redirect fix + `gravitas.egg-info` artifacts in diff | `classify_shell('echo hi>out.txt')` → mutation; corpus+tests on main; suite OK; CI HEAD green | close superseded via #48 |
| #35 | #12 | 62b2af3 CONFLICT; Gate 3.12 FAILURE | dangerous-env fix, large diff vs stale base | `LD_PRELOAD=… ls`, `GIT_PAGER=…` → mutation; suite OK | close superseded via #48 |
| #36 | #13 | e21900c CONFLICT; Gate 3.12 FAILURE | wrapper-flag fix | `sudo -n rm x` → destructive; suite OK | close superseded via #48 |
| #37 | #28 | 1db24e9 CONFLICT; own CI green | impact root-escape fix | `../outside` → None, in-root normalizes, graph excludes escapes; `test_impact_graph.py` green | close superseded via #48 |
| #38 | #19 | 1ef2443 CONFLICT; own CI green | replan delegation fix | `decide({'repeated_failures':2})` → replan/none/no risky-implementation | close superseded via #48 |
| #39 | #18 | 70b5ef0 CONFLICT; own CI green | direct-path delegation fix | direct records now carry `parallel-workstreams-…`/`localization-uncertain` codes | close superseded via #48 |
| #40 | #20 | 72c0d34 CONFLICT; own CI green | fail-closed mode fix | `normalize_mode('bogus'/' '/None/123)` → `answer` | close superseded via #48 |
| #41 | #17 | af92f79 CONFLICT; own CI green | cargo-check fix | `cargo check` → mutation; `test_action_cargo.py` green | close superseded via #48 |
| #46 | #29 | fcef224 CONFLICT; own CI green | exact-match fix | `legacy_requirement_met` uses `shlex.join` equality; `/bin/echo latest` no longer satisfies `test` | close superseded via #48 |
| #47 | #30 | 2273801 CONFLICT; own CI green | argv-array schema fix | `schemas/contract.json` validator command = array; both schemas agree | close superseded via #48 |
| #49 | #50 | ac651fa CONFLICT; own checks empty | windows portability | backslash normalization on main; `ECHO_COMMAND=[sys.executable,…]` fixture; suite OK | close superseded via #53 |
| #51 | #22 | 3b65560 MERGEABLE; own CI green (dup) | UNKNOWN_WRITE_TIME fail-closed | sentinel + `is_fresh` fail-closed on main; regression tests green | close superseded via #53 |
| #52 | #23 | 6a929b2 MERGEABLE; own CI green (dup) | shell write-record emission | `post_tool.py` emits `source:write`; freshness-invalidation test green | close superseded via #53 |

Note: #51/#52 heads are not ancestors of main (#53 squash-merged equivalent content). Re-merging any of the 13 would duplicate landed changes; #34 would additionally reintroduce `gravitas.egg-info` artifacts.

## Issue dispositions (15 open)

| Issue | Fix vehicle | Verified on main | Action |
|----|----|----|----|
| #12 dangerous env | #48 (#35) | probe: mutation; tests green | close completed |
| #13 wrapper flags | #48 (#36) | probe: `sudo -n rm x` destructive; tests green | close completed |
| #17 cargo check | #48 (#41) | probe: mutation | close completed |
| #18 direct delegation | #48 (#39) | probe: codes present | close completed |
| #19 replan stakes | #48 (#38) | probe: no spurious reviewer | close completed |
| #20 unknown mode | #48 (#40) | probe: → `answer` | close completed |
| #21 forged validator | #48 (#42) | `declared_validator_pass` binds argv; `test_stop_gate_rejects_forged_validator_command` green; chain stays unkeyed (documented in `evidence_chain.py`: tamper-evident, not tamper-proof) | close completed w/ limitation noted |
| #24 missing contract | #48 (#44) | `load_contract`→None→`continue` | close completed |
| #25 init validation | #48 (#45) | `init_session.validate_contract` denies unknown modes | close completed |
| #26 zero criteria | #48 (#43) | empty criteria→`continue` | close completed |
| #27 bench honesty gate | none | **HOLE REPRODUCED**: `cmd_report`→`validate_episodes(dir)` (no schema) accepts `functional_solve:true`+FAIL episode | **leave open**; assign MDADILIFTEKHAR per request |
| #28 impact escapes | #48 (#37) | probes + `test_impact_graph.py` green | close completed |
| #29 substring match | #48 (#46) | exact-match code + tests green | close completed |
| #30 schema argv | #48 (#47) | schema=array; runner/gate consistent | close completed |
| #50 windows | #53 (#49) | backslash→POSIX normalization; interpreter fixtures; suite green. No Windows runner in CI (ubuntu-only), so on-Windows execution itself not re-run here | close completed w/ scope noted |

Closed issues (#4,#6,#11,#14,#15,#16,#22,#23) spot-checked still present on main (jsonc guard, allowlist flag edges, redirect/env/wrapper/cargo classification, git-config/sed handling, UNKNOWN_WRITE_TIME, write-record emission). Closed PRs: no duplicate actions; #42–#45 content confirmed live via #48.

## Test commands run
- `/Users/uday/Gravitas/.venv/bin/python -m unittest discover -s tests` in clean `origin/main` worktree → Ran 250 tests, OK
- Targeted behavior probes (classify_shell / decide / normalize_mode / impact_graph / stop_gate paths) → all match acceptance
- Live #27 repro → contradictory episode accepted by report path (hole confirmed)
- `gh api …/commits/58c0bf6/check-runs` → 3/3 success on HEAD
- Not run: on-Windows execution (no Windows runner available/CI ubuntu-only); contributor Windows repro taken as reported
