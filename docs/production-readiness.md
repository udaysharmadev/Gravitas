# Gravitas Production-Readiness Assessment

## Executive finding

**Release decision: BLOCKED.** Gravitas has a credible policy kernel, a useful runtime prototype, deterministic local tests, and substantial benchmark infrastructure. It does not yet have the live-host, security-boundary, distribution, or comparative-model evidence required for a production claim.

This decision separates three products that were previously conflated:

| Product surface | Current maturity | Production claim allowed? |
|---|---|---|
| Portable Agent Skill | Usable research preview | Yes, as an instruction workflow |
| Antigravity runtime hooks | Release candidate | No, pending live-host and adversarial validation |
| Claude-like Gemini engineering behavior | Research hypothesis | No, pending eligible paired results |

The highest-priority work is not additional marketing. It is closing the evidence gap between the behavior described in public documentation and the behavior observable from an installed Antigravity environment.

## Scope and standard of proof

The assessment covered:

- Agent Skill structure and activation;
- Antigravity plugin layout and hook I/O contracts;
- runtime action locking, scope checks, evidence collection, recovery, and stop gating;
- task, evidence, and episode schemas;
- unit tests, action-lock corpus, CI, and benchmark tooling;
- installation and packaging paths;
- security, privacy, licensing, governance, and support documents;
- public benchmark and model-comparison claims;
- research provenance and reproducibility.

Production readiness requires evidence from the installed host, not only source-level unit tests. This follows the central result of Harness-Bench: capability and failure behavior vary across the combined model-and-harness configuration, and execution traces plus final artifacts are needed to diagnose that behavior.^1 Harness-IF further shows that apparent rule compliance can reflect a model's prior behavior rather than the configured instruction surface, so rules must be evaluated against withheld-rule controls and execution evidence.^2

## Research findings

### Skills are an appropriate delivery surface

The open Agent Skills specification defines a skill as a directory containing `SKILL.md`, with optional scripts, references, and assets. It requires `name` and `description`, recommends progressive disclosure, and recommends keeping the primary file below 500 lines and roughly 5,000 tokens.^3 Gravitas's core skill is within that size envelope and correctly separates detailed procedures into references and resources.

Antigravity adopted the open Agent Skills standard and discovers workspace skills under `.agents/skills/<skill-folder>/SKILL.md` and global skills under `~/.gemini/config/skills/<skill-folder>/SKILL.md`.^4 This makes the repository's `.agents/skills/gravitas` copy a valid development activation surface, provided it remains synchronized with the canonical skill.

### Prompt policy cannot establish hard enforcement

Agent Skills guidance warns that every instruction competes for model attention and that overly comprehensive skills can reduce performance.^5 It also recommends adding only the knowledge the agent lacks, using explicit decision trees, and testing execution traces rather than judging final prose. Gravitas's progressive policy kernel follows this direction, but any claim that it *forces* exact behavior exceeds what a prompt surface can prove.

The appropriate claim is behavioral and measurable: Gravitas is intended to make
Gemini more likely to exhibit the engineering discipline users associate with
Claude—reconnaissance, proportionate planning, verification, recovery, and
honest reporting. Mechanical guarantees must come from correctly installed
hooks, host permissions, sandboxes, and deterministic validators.

### The harness thesis is plausible but unmeasured for Gravitas

ReAct supports interleaving reasoning, action, and observation rather than relying on ungrounded generation.^6 Plan-and-Solve supports decomposition before multi-step execution.^7 Reflexion supports retaining structured feedback from failed attempts.^8 Chain-of-Verification supports separating verification from the initial draft.^9 These sources motivate Gravitas's design choices.

They do not transfer their reported effect sizes to Gemini repository work. A Gravitas-specific improvement claim needs a controlled model+harness benchmark with fixed tasks, budgets, validators, and release artifacts.

## Evidence observed in the repository

### Working foundation

- A standards-shaped core skill with a clear activation description.
- Five memorable engineering rules with risk-adaptive execution.
- Structured task contracts and JSON schemas.
- Antigravity-oriented PreToolUse, PostToolUse, PostInvocation, and Stop scripts.
- Local state, coverage, evidence, failure, impact, and recovery primitives.
- Ten benchmark lanes and 30 registered task specifications.
- Validators, summarization, paired comparison, bootstrap, and audit tooling.
- A deterministic action-lock corpus and runtime/benchmark unit tests.
- MIT license, security policy, governance, support, citation, and contribution files.

### Evidence that is not yet present

- No eligible paired model-comparison dataset is published.
- No raw production trajectories substantiate performance or parity statements.
- No live Antigravity installation transcript proves plugin discovery and hook lifecycle behavior.
- No concurrent-session, symlink, shell-scope, secret-scrubbing, or cross-platform adversarial report exists.
- No signed/tagged release corresponds to the earlier v4 production language.
- No independent reproduction has been published.

## Blocker register

### P0 — trust and claims

#### Comparative performance claims

The README labels Gravitas a research preview and reports no comparative effect.
Production comparison claims remain blocked until every published result includes
sample size, runs per configuration, versions, date, confidence intervals, raw
data, failures, evaluator version, and dataset commit.

#### Model-identity claim

“Makes Gemini think exactly like Claude” is not operationally measurable and confuses workflow similarity with model equivalence. It also cannot be established from tone or visible reasoning syntax.

Disposition: retain the user-facing aspiration—Gemini working more like a careful
Claude-style engineering agent—but define it through observable controls: recon
completeness, plan quality, validator execution, scope adherence, false-completion
rate, regression rate, and evidence integrity.

### P0 — host integration

#### Hook payload incompatibility

Antigravity 2.0 documents `toolCall.name`, `toolCall.args`, camelCase common fields, `deny` for hard PreToolUse blocking, `{}` from PostToolUse, and `continue` for Stop gating.^10 The original scripts consumed preview-style `tool_name` and `tool_input`, returned `block`, and emitted no PostToolUse JSON.

Disposition: source compatibility has been repaired and regression tests added. Remaining gate: install the plugin in a clean Antigravity 2.0/CLI environment and archive the `/hooks` output plus one allow, deny, ask, post-tool, post-invocation, and stop trajectory.

#### Plugin layout

Antigravity documents a plugin root containing `plugin.json`, optional `hooks.json`, `skills/`, and `agents/` components.^11 The repository previously kept hook configuration under a nested non-root path and used a manifest schema with fields rejected by the documented Antigravity schema.

Disposition: a root host manifest and `hooks.json` now exist. Remaining gate: clean-install verification from the exact public distribution artifact.

### P0 — safety boundary

#### Shell mutation scope

Direct file-edit tools can be checked against resolved allowed paths. Arbitrary shell commands cannot be reliably scoped with a regular expression: `sed -i`, `tee`, scripts, interpreters, build hooks, symlinks, and subprocesses can write indirectly.

Required production decision: either (a) treat shell execution as outside the write-scope guarantee and say so, (b) require host sandbox policies that constrain filesystem access, or (c) route mutating work through a restricted command executor. Do not claim a hard repository security boundary from string matching.

#### Session isolation

Runtime scripts now derive a stable, hashed directory name from Antigravity's
`conversationId` when it is present, so two supplied conversation IDs do not
select one another's ledgers. Legacy payloads without a conversation ID retain a
compatibility fallback to the newest session and are not safe for concurrent use.

Remaining gate: prove the official host field is present across supported hook
lifecycle events, define explicit workspace selection for multi-root projects,
lock ledger writes, and run a live two-conversation trace.

#### Evidence integrity

The stop gate previously accepted hook-created command entries by matching command text and success metadata. That was not an evidence boundary: the documented PostToolUse payload does not guarantee stdout or an exit code.

Current mitigation: `validator_runner.py` now owns validator execution and records
validator ID, criterion IDs, exit code, command/output digests, git snapshot,
and a hash-linked event. The stop gate accepts only passing runner records.
The runner rejects validator IDs, criterion IDs, and commands that are not
declared by the session contract. PostToolUse data remains diagnostic telemetry.
The ledger has advisory locking
and tamper-evident chaining, not cryptographic custody: a process able to rewrite
the harness or ledger remains in the trusted computing base.

### P1 — runtime robustness

#### Fail-open behavior

Malformed PreToolUse input previously returned allow, and the stop gate allowed termination after three unsuccessful cycles. Both weaken a claimed enforcement layer.

Disposition: PreToolUse now denies malformed input, and the completion circuit breaker no longer converts missing proof into success. Remaining gate: define a recoverable operator flow so fail-closed behavior cannot trap a conversation indefinitely.

#### Task identifier traversal

The original initializer used an unvalidated task ID as a path segment.

Disposition: task IDs are constrained to a bounded safe character set and traversal has a regression test.

#### Ledger schema mismatch

Runtime read/write and command events originally failed the published evidence schema because they omitted criterion fields and used undeclared properties.

Disposition: the schema now distinguishes runtime events from criterion-linked proofs. Remaining gate: validate every emitted JSONL entry during unit and integration tests.

#### Secret retention

Post-tool records redact common bearer-token, API-key, password, and secret
assignments before persistence. Test output and command errors may still contain
unknown credential formats, paths, customer data, or source fragments.

Required fix: default to hashes and structural metadata; add configurable redaction; test common API-key, credential, email, and authorization-header patterns; document retention and deletion.

### P1 — distribution and operations

#### Activation-copy synchronization

The canonical skill and `.agents/skills/gravitas` activation copy are checked
byte-for-byte in CI. The remaining design trade-off is duplication for host
compatibility; any change must update both copies in the same pull request.

#### Python runtime distribution

`pyproject.toml` exposes the `gravitas` console command and CI installs it before
its smoke test. Native hook scripts are intentionally run from the reviewed
plugin checkout, not represented as a standalone sandboxed security product.
Remaining gate: wheel inspection and clean-environment install coverage across
the supported Python/platform matrix.

#### CI coverage

The current CI runs unit tests and a registry/schema audit. A production gate also needs:

- supported Python version matrix;
- format/lint/static checks;
- generated-ledger schema validation;
- manifest and hook-configuration validation;
- clean plugin install and smoke lifecycle;
- claim-regression checks;
- secret scan and dependency review;
- Linux/macOS coverage and a declared Windows position;
- benchmark-release audit that fails when claimed results lack raw data.

### P1 — benchmark publication

The synthetic implementation fixture is appropriate for runner plumbing but explicitly ineligible for a product comparison. The 30-task manifest is a registry, not 30 completed benchmark cases.

A minimum credible release should include:

1. A frozen benchmark version and task-selection rationale.
2. Licensed repositories and immutable starting commits.
3. Hidden deterministic acceptance and regression validators.
4. Fixed host, model, effort, tool, permission, and quota configurations.
5. Paired runs across baseline and treatment, with order randomization where possible.
6. Infrastructure failures marked invalid rather than silently removed or counted as agent failure.
7. Functional solve, false completion, scope, regression, evidence-integrity, latency, token, and cost outcomes.
8. Paired confidence intervals and McNemar-style inference for binary outcomes.
9. All failures, not only wins.
10. Raw trajectories and an independently runnable evaluator.

## Production acceptance gates

| Gate | Required proof | Status |
|---|---|---|
| G1 — public claims | Automated scan plus claims register; no unsupported results | Improved; full docs sweep pending |
| G2 — skill conformance | `skills-ref validate`; trigger/non-trigger evaluation | Pending canonical validator run |
| G3 — plugin install | Clean `agy plugin install`, `plugin list`, `/hooks` capture | Pending |
| G4 — hook lifecycle | Official payload fixtures and live allow/deny/ask/post/stop trace | Unit portion improved; live pending |
| G5 — scope boundary | Threat model plus shell/symlink/multi-root tests | Pending |
| G6 — session isolation | Two concurrent conversation IDs with no state crossover | Local regression pass; live pending |
| G7 — evidence integrity | Runner-owned exit-code evidence, hash-linked ledger, repository snapshot | Partial — needs hostile concurrent-session and installed-host tests |
| G8 — privacy | Redaction tests, retention policy, secret scan | Local redaction tests pass; broader scan pending |
| G9 — portability | Supported host/Python/platform matrix | Pending |
| G10 — benchmark | Eligible paired dataset with raw episodes and statistics | Pending |
| G11 — independent verification | External reproduction of install and headline benchmark | Pending |
| G12 — release engineering | Tag, changelog, artifact checksum, rollback notes | Pending |

## Recommended release sequence

### Milestone A — honest preview

- Merge the corrected README and claims language.
- Publish the source-level test output and known limitations.
- Describe skill-only and native modes separately.
- Label runtime hooks experimental.

Exit: users can evaluate the workflow without being misled.

### Milestone B — native beta

- Bind sessions to conversation IDs.
- harden scope, symlink, concurrency, and failure recovery behavior;
- validate every ledger event;
- add redaction and retention controls;
- demonstrate clean Antigravity installation and lifecycle traces.

Exit: invited users can run native hooks with a documented threat model.

### Milestone C — benchmark release

- Replace placeholder/synthetic cases with eligible tasks;
- freeze configurations and collect paired runs;
- publish raw trajectories, failures, statistics, and evaluator;
- obtain independent reproduction.

Exit: Gravitas may publish narrow, versioned effect estimates for the exact evaluated model+harness configurations.

### Milestone D — production

- close all P0 and P1 blockers;
- run the full release matrix from a clean artifact;
- tag the release and archive benchmark data;
- publish rollback and support commitments.

Exit: production-ready may be stated for the specifically tested surfaces—never as universal model equivalence.

## Product positioning after the audit

Recommended promise:

> Gravitas is a verification-first engineering workflow for coding agents. It combines a portable Agent Skill with optional Antigravity runtime checks for read-before-write discipline, task contracts, evidence-backed completion, and recovery. Its comparative impact on Gemini is being measured through an open trajectory-level benchmark.

Avoid:

- exact imitation of another provider's model;
- universal “better” or “parity” statements;
- percentages without raw eligible episodes and uncertainty;
- describing regex command checks as a security sandbox;
- calling registered task metadata completed benchmark runs.

## Sources

1. Yao et al. “[Harness-Bench: Measuring Harness Effects across Models in Realistic Agent Workflows](https://arxiv.org/abs/2605.27922).” 2026.
2. Huang et al. “[Harness-IF: Evaluating Instruction Following Across Instruction Surfaces in Coding Agents](https://arxiv.org/abs/2608.11727).” 2026.
3. Agent Skills. “[Specification](https://agentskills.io/specification).” Accessed 2026-09-11.
4. Google. “[Antigravity Agent Skills](https://antigravity.google/docs/skills).” Accessed 2026-09-11.
5. Agent Skills. “[Best practices for skill creators](https://agentskills.io/skill-creation/best-practices).” Accessed 2026-09-11.
6. Yao et al. “[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629).” 2022.
7. Wang et al. “[Plan-and-Solve Prompting](https://arxiv.org/abs/2305.04091).” 2023.
8. Shinn et al. “[Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366).” 2023.
9. Dhuliawala et al. “[Chain-of-Verification Reduces Hallucination in Large Language Models](https://arxiv.org/abs/2309.11495).” 2023.
10. Google. “[Antigravity Hooks](https://antigravity.google/docs/hooks).” Accessed 2026-09-11.
11. Google. “[Antigravity Plugins](https://antigravity.google/docs/plugins).” Accessed 2026-09-11.
