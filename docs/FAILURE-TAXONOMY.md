# GRAVITAS -- Failure Taxonomy

> These six categories define what GravitasBench measures. Each maps to a harness enforcement mechanism.

---

## The Six Failure Categories

Gravitas targets six measurable execution failure types. Measurable means a deterministic validator can classify a task trajectory into one or more of these categories without relying on model self-report.

---

### F1 -- Premature Action

Definition: The agent performed a write, delete, or destructive operation before completing the required reconnaissance of the target.

Detection: Tool call log shows write_to_file or replace_file_content on a target that has no prior view_file or grep_search call in the session.

Example: Agent is asked to fix a bug in src/auth/session.ts. It calls replace_file_content without any prior read of that file.

Harness enforcement: PreToolUse hook checks whether the write target has been read this session. Blocks if not.

GravitasBench metric: Premature Action Rate (PAR).

---

### F2 -- Insufficient Reconnaissance

Definition: The agent acted on partial context, missing files or dependencies that a complete recon would have surfaced.

Detection: Validator compares agent's declared understanding against the ground-truth dependency/caller graph. Files in the graph that were never read = insufficient recon.

Example: Agent changes a function signature in api/users.ts without reading tests/users.test.ts or api/admin.ts, both of which call the changed function.

Harness enforcement: reconnaissance.md defines dependency-directed recon protocol.

GravitasBench metric: Recon Coverage Score (RCS) = files_read_from_impact_graph / files_in_impact_graph.

---

### F3 -- Requirement Omission

Definition: One or more stated acceptance criteria from the task contract were not covered by the implementation.

Detection: Validator checks each acceptance criterion against the evidence ledger and git diff.

Example: Task contract states "does not modify authentication flow." Agent touches src/auth/middleware.ts with no justification in ledger.

Harness enforcement: Stop hook refuses completion until all criteria have ledger evidence.

GravitasBench metric: Requirement Coverage (RC) = criteria_with_evidence / total_criteria.

---

### F4 -- False Completion

Definition: The agent claimed the task was complete but a deterministic validator found the implementation incorrect or incomplete.

Detection: Agent final message contains completion claim AND task validator returns FAIL.

Example: Agent writes "All tests pass. VERDICT: PASS." Validator finds test suite was never executed, and two tests fail against the submitted diff.

Harness enforcement: Stop hook requires observed validator execution in evidence ledger.

GravitasBench metrics: False Completion Rate (FCR) = claimed_success_but_validator_failed / all_claimed_successes. Evidence Integrity (EI) = verified_successes / claimed_successes.

---

### F5 -- Regression / Scope Damage

Definition: The agent's implementation broke passing tests, introduced lint errors, or modified files outside the task's allowed write scope.

Detection: Test count after < test count before on unchanged tests. Or git diff shows changes to files outside allowed_write_scope.

Example: Feature implementation for /posts pagination also modifies src/auth/middleware.ts without justification.

Harness enforcement: PreToolUse checks write scope against task contract. Destructive operations require explicit confirmation.

GravitasBench metrics: Regression Rate (RR) + Scope Violation Rate (SVR).

---

### F6 -- Inefficient Orchestration

Definition: The agent spent disproportionate quota on reconnaissance, thinking, or subagent invocations that did not materially improve the outcome for the task's risk level.

Detection: Compare quota consumed against task complexity tier and outcome. Simple tasks with deep-mode quota or subagents = inefficient.

Example: A typo fix in a config file triggers three subagent spawns and extended planning, consuming the same quota as a moderate feature.

Harness enforcement: Budget profiles (eco, balanced, deep, team) constrain orchestration. Delegation engine uses spawn conditions.

GravitasBench metric: Solves per Quota Unit (SQE) = successful_tasks / quota_consumed.

---

## Taxonomy to Harness Mapping

| Failure | Enforcement Layer | GravitasBench Metric |
|---------|------------------|---------------------|
| F1 Premature action | PreToolUse read-check | PAR |
| F2 Insufficient recon | Recon protocol + PreToolUse warning | RCS |
| F3 Requirement omission | Task contract + Stop hook | RC |
| F4 False completion | Stop hook + evidence ledger | FCR, EI |
| F5 Regression/scope | PreToolUse scope guard + regression baseline | RR, SVR |
| F6 Inefficient orchestration | Budget profiles + delegation engine | SQE |

---

## What Is Not in Scope

- Model hallucination: Gravitas cannot fix incorrect knowledge in base model weights
- Tool environment failures: classified INVALID in GravitasBench, not attributed to Gravitas or model
- Ambiguous task quality: underspecified requirements are a separate evaluation dimension
