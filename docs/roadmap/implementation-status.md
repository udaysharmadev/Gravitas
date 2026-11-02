# Implementation Status

Branch work for the ascension mission. Updated per session with observed
evidence only.

## Completed + verified (tests observed this session)
- Benchmark honesty gate: schema-required `validate_episodes`, schema-loaded
  `cmd_report` with exit 1 on contradiction/empty, aggregate-skip in
  `compare`/`metrics`. Evidence: `.venv/bin/python -m unittest discover -s
  tests` → 256 OK; 6 new tests (was 250).
- OpenCode read parity: shim per-session read ledger + guard enforcement with
  session isolation and corrupt-line tolerance. Evidence: same 256-test run;
  `node --check` on the shim; new `GuardTests` (allow after read, cross-session
  deny).

## Implemented, needs reviewer merge decision
- Contributor PR #56 overlaps the benchmark gate (commented with a test-purity
  note). This branch's version additionally covers empty datasets and
  aggregate-skip with schema-clean fixtures. Merge one, close #27 with the
  winner.

## In progress
- GitHub roadmap: 25 issues #57-#81 filed with code-level evidence, attack
  sketches, acceptance criteria and verified references. #64 tracks the
  full-text literature pass; #70 the lifecycle corpus; #66 the first
  licensed-task bar; #79 the first ablation experiment (needs model budget).
- Recovery-doc contradiction fix (F9, #57) — unassigned.
- Full-text paper review (#64) — unassigned; contributor-ready in small batches.

## Blocked
- Live model-backed benchmark comparison (no quota configured; correctly not
  attempted).

## Proposed only
- Systems 1–7, 9–10 vertical slices (context scout, spec forge, adaptive
  controller beyond `decide`, patch tournament, adversarial verifier, decision
  memory, trace linter, offline optimizer).

## Rejected
- None yet. Vector-DB default, mandatory planning ceremony, and autonomous
  self-modification are pre-rejected pending counter-evidence.

## Next actions
1. Create ~10 scoped GitHub issues with acceptance criteria + tests.
2. Fix F9 doc contradiction.
3. Rebuild `dist/` via build scripts if the shim ships there (verify, don't hand-patch).
