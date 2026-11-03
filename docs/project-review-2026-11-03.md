# GRAVITAS project review — 2026-11-03

## Executive summary

GRAVITAS is a **model-agnostic reliability runtime for coding agents**, not
a new model or a replacement coding agent. Its portable skill teaches six
invariants; optional host hooks and a shared policy engine enforce the
machine-checkable subset. Owned validators, an evidence ledger, and a
completion gate turn some agent claims into inspectable execution records.

The project has meaningful implementation depth, a healthy local baseline,
and explicit research-preview positioning. Its strongest near-term upgrade
is evidence correctness, not more prompt instructions or a larger task-ID
count. This review identified reproducible false-completion and benchmark
publication paths; the accompanying patch hardens those boundaries.

**No separate Codex CLI/API or live model-backed benchmark was invoked for
this work.** Public documentation and GitHub were read only. Repository
verification used local tools and provider-mocked tests, not paid benchmark
runs. No commits, pushes, release publication, or dependency upgrades were made.

## Scope and evidence

The starting checkout was `f1a73b105537444d1e2ddd9d20f951aa653e6910` on
`ascension/phase-b-foundation`, with a clean working tree. It contained
617 tracked files, including generated distribution assets and historical
benchmark artifacts. Three read-only reviews covered the runtime/adapters,
benchmark/evaluation pipeline, and packaging/CLI/CI. The implementation
phase then read the selected targets, callers, tests, and architecture
records directly.

Baseline, executed locally on macOS with Python 3.14.6:

```text
Ran 391 tests in 19.666s
OK
```

Research also covered the public repository's open roadmap issues,
primary documentation, seven research abstracts, and pinned source
interfaces from comparable open-source projects. This is a broad,
reproducible engineering assessment, **not an exhaustive audit of every
line or a certification of live host behavior**. Abstract-level findings
are identified as such; no external paper's numerical result is evidence
for GRAVITAS.

## Architecture and product summary

| Layer | Responsibility | Main sources |
|---|---|---|
| Portable kernel | Ground before edits, declare scope, verify claims, avoid exact failed retries, satisfy criteria, label uncertainty | `skills/gravitas/SKILL.md`, `AGENTS.md` |
| Action/policy runtime | Normalize host actions; classify shell capabilities; apply mode, scope, read, and retry rules | `plugins/gravitas-antigravity/scripts/gravitas_action.py`, `gravitas_policy.py` |
| Verification/evidence | Discover checks; run exact declared argv; record bounded output digests and hash-linked events; reduce criterion states | `validator_runner.py`, `gravitas_verify.py`, `gravitas_evidence.py`, `evidence_chain.py` |
| Lifecycle/recovery | Isolate native conversations; persist state; block incomplete work; expose deficits and bounded unverified termination | `session_context.py`, `post_invocation.py`, `stop_gate.py`, `child_session.py` |
| Host integration | Native Antigravity hooks; OpenCode before/after shim and permission profiles | `plugins/gravitas-antigravity/hooks.json`, `adapters/opencode/` |
| User/distribution surface | `doctor`, `init`, `decide`, `validator`, `repro`, `guard`, `verify`, and maintenance commands | `gravitas_cli.py`, `gravitas_init.py`, `pyproject.toml` |
| Evaluation | Task registry, synthetic implementation runner, withheld acceptance, outcome validation, paired reports | `benchmarks/`, `eval/`, `schemas/` |

Architectural decisions favor a small deterministic runtime rather than a
large agent framework. Planning is conditional; risk, effort, context, and
verification depth are distinct. See
[ADR-0003](adr/0003-layered-runtime.md),
[ADR-0004](adr/0004-kernel-policy.md),
[ADR-0006](adr/0006-verification.md), and
[ADR-0010](adr/0010-bench-evidence.md).

### Guarantees versus boundaries

- Native Stop checks owned evidence, freshness, declared validators,
  unresolved failures, background work, and incomplete registered children.
  Circuit-breaker termination is explicitly unverified, not a PASS.
- Evidence hashes plus user-local anchors detect some rewrites while the
  anchor store remains trustworthy. They do not resist a same-user process
  that can rewrite both the ledger and anchors.
- Scope enforcement covers dedicated file tools and shell operands the
  classifier can enumerate. Arbitrary subprocess effects are not contained
  by an operating-system sandbox.
- Freshness is global ledger timestamp ordering, not a complete verified
  content snapshot of every source dependency.
- Portable skills are instructions, not enforcement. OpenCode lacks the
  native automatic Stop equivalent, and its live payload/version behavior
  still needs separate validation.

## Benchmark reality

The manifest registers **48 tasks in 10 lanes**: 30 core, 5 negative, 5
trap, and 8 harvested. There are 62 task YAML files including unregistered
pilot/canary/example specifications, and three L10 holdouts.

Those counts overstate executable diversity if read as implemented tasks:
`benchmarks/runner/fixtures.py` maps task IDs onto only **five distinct
synthetic acceptance exercises**. `implementation.py` materializes those
Python fixtures; it does not check out and execute the repository named by
a HARV specification. For example, HARV-008 describes an AVA/JavaScript task
from `escape-string-regexp`, while the current runner still exposes
`src/target.py`.

Harvested `hidden_validator_hash` metadata currently hashes task ID plus
criterion prose, rather than an executable hidden-test artifact. HARV-001
also pins `1060974…`, although its described `simulated_approver.py` target
was introduced later in `3138d92`. These are provenance/integration gaps,
not evidence that models fail those real tasks.

No current result files are tracked under `benchmarks/results/`; historical
runs are quarantined as invalid methodology, and local canary aggregates
are not release episodes. Configuration/ablation names are declared, but
the synthetic runner does not apply the full host/skill/hook experiment
matrix. There is **no verified model-performance improvement to report**.

## Delivered upgrade

### 1. Latest-validator correctness and consistent recovery

Before: a ledger containing `unit PASS`, `lint PASS`, `unit FAIL`, then
`lint PASS` could return verified Stop `allow`. The reducer selected the
latest verdict across validators, and the gate accepted any older fresh
PASS for each required validator. A failing criterion could also remain
in recovery state's `completed_criteria`.

Now: owned executions are reduced per validator in ledger order. A newer
FAIL or malformed/nonmatching execution revokes earlier criterion credit,
including runs that omit criterion binding. Every explicitly assigned
validator must supply fresh declared evidence; another validator cannot
mask a failure. Separate successful bindings from the same validator remain
usable until a later failure/write invalidates them. Stop also uses latest
results for required validators and exact legacy requirements. Recovery
coverage, completed criteria, and pending criteria use the same reducer.

Sources: `gravitas_evidence.py`, `stop_gate.py`, `post_invocation.py` under
`plugins/gravitas-antigravity/scripts/`.

### 2. Benchmark outcome integrity

Before: the implementation producer marked a denied simulated Tier-2
checkpoint unsolved, but outcome reconstruction ignored that checkpoint.
Rewriting the episode's flags to claim success could make it validate.
Duplicate criterion names could likewise overwrite an earlier failure or
INVALID result, and component checks could miss compensating false values.

Now: every recorded validator is mandatory. `tests_passing` remains the
hidden-test result; a separate `validators_passing` field represents the
complete set. Producers and validation share that rule. Validation rejects
duplicate/malformed criteria, missing disclosed checkpoints, malformed
component types, false derived flags, and individually inconsistent known
components. Legacy preview episodes and four-argument outcome callers remain
supported.

Sources: `benchmarks/runner/outcome.py`, `implementation.py`, `run.py`,
`validate.py`, and `episode.schema.json`.

### 3. Fail-closed publication eligibility

Before: 30 paired run indices of **one smoke task** passed the publication
gate, despite documentation explicitly excluding synthetic evidence.

Now: eligibility requires explicit repository evidence and provenance,
unique episode identities, matching task/model/host/evaluator inputs,
consistent experiment revisions, at least 30 distinct tasks, and at least
five valid paired runs per task. Smoke/synthetic/missing provenance remains
preview-only. Reports explain blockers; rejected publication requests return
a clean CLI error before creating report artifacts. Every displayed
configuration must have a checked comparison; report writing recomputes
eligibility from supplied episodes. INVALID classification cannot hide
malformed outcome evidence from these checks.

This is a **structural gate**, not authenticated provenance or a statement
of statistical significance. No current built-in runner emits eligible
repository evidence. See [the full methodology](benchmark.md) for fields,
compatibility, and custody limitations.

### 4. Registry-backed public disclosure

The README claims checker required the obsolete literal count of 30 tasks,
which conflicted with the manifest's 48. It now derives task/lane counts
from the registry and rejects inconsistent manifest counts; the existing
unsupported-claim denylist is preserved. Regression tests cover current and
stale disclosures without editing the real README during tests.

### Verification design

`tests/test_upgrade_integrity.py` includes actual local validator subprocess
lifecycles, in-memory ledger reduction, provider-mocked implementation
round trips, and publication positive/negative fixtures. The original code
failed the regressions; an owned reproducer records the before-fix failure.
The same command is rerun after changes, followed by owned full verification
and generated-bundle parity checks. Test-only repository metadata is not
published evidence and never calls a model.

## External research and implications

### Primary standards and operational documentation

1. **[Agent Skills specification](https://agentskills.io/specification).**
   Requires a skill directory with `SKILL.md`, valid name/description
   frontmatter, and naming constraints; recommends progressive disclosure
   and a main file under 500 lines. The portable kernel already follows
   the small-kernel direction. This specification does not confer host
   enforcement or reliability guarantees.
2. **[OpenCode plugins](https://opencode.ai/docs/plugins/) and
   [permissions](https://opencode.ai/docs/permissions/).**
   Public docs describe `tool.execute.before`, `tool.execute.after`, session
   events, sequential hook loading, and last-matching permission rules.
   Permission defaults can be permissive, and auto-approval does not override
   explicit deny. Versioned payload fixtures are essential; documentation
   alone cannot prove that an installed shim receives the expected arguments.
3. **[PyPA src versus flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
   and [setuptools data files](https://setuptools.pypa.io/en/latest/userguide/datafiles.html).**
   Running tests in a source checkout can hide broken installed imports or
   omitted assets. Data-file lookup must respect installation schemes.
   Fresh outside-checkout install/init tests have higher value than a
   packaging-layout rewrite without reproduction.
4. **[Python version lifecycle](https://devguide.python.org/versions/).**
   Python 3.9 is end-of-life. GRAVITAS still promises `>=3.9`, while CI tests
   Ubuntu on 3.9/3.12. Retaining that compatibility is not the same as
   upstream support. Decide and document the support policy before making a
   breaking minimum-version change; add current-Python/platform tests.
5. **[SWE-bench evaluation](https://www.swebench.com/SWE-bench/guides/evaluation/).**
   Evaluation applies patches to real repositories and executes tests in
   Docker; predictions identify task, model, and patch. Cached results are
   keyed by run and instance, requiring a new run ID for a changed patch.
   This supports reproducible real-repository execution and exact run
   identity—not borrowing a leaderboard result for GRAVITAS.

### Literature checked at abstract level

The following titles and abstracts were fetched directly from arXiv. The
underlying studies were not replicated, and full-paper methods/supplements
were not independently audited in this task.

| Source | Relevant finding reported by the authors | Implication for GRAVITAS |
|---|---|---|
| [SWE-agent, 2405.15793](https://arxiv.org/abs/2405.15793) | Agent-computer interface design affects repository navigation, editing, and test execution. | Validate tool and feedback surfaces, not only prompt wording. |
| [Agentless, 2407.01489](https://arxiv.org/abs/2407.01489) | Localization, repair, and patch validation can form a strong simple baseline; dataset issues can contaminate evaluation. | Compare with simple deterministic baselines; inspect task provenance. |
| [Harness Engineering source study, 2609.00006](https://arxiv.org/abs/2609.00006) | Eleven systems share runtime subsystems and recurring patterns; policy moves from prose toward configuration. | Reuse a subsystem taxonomy; distinguish enforced rules from advice. |
| [Agentic Harness Engineering, 2604.25850](https://arxiv.org/abs/2604.25850) | Observability and falsifiable edit predictions support harness evolution; reported ablations favor tools/middleware/memory over prompt changes. | Keep upgrades scoped, reversible, measured, and linked to regression evidence. |
| [Harness-IF, 2608.11727](https://arxiv.org/abs/2608.11727) | Against-prior instruction following is weaker than aggregate compliance; instruction surface affects precedence. | Prove machine-checkable rules using traces and negative cases. |
| [The Scaffold Effect, 2607.22585](https://arxiv.org/abs/2607.22585) | Harness choice changes cost, latency, and failure patterns; model-only labels hide variation. | Pin model+harness configurations and measure cost per solved task. |
| [Harness-Bench, 2605.27922](https://arxiv.org/abs/2605.27922) | Artifacts, traces, usage, and validators reveal process failures beyond final completion. | Preserve outcome fidelity before expanding metrics or publishing comparisons. |

### Pinned comparable systems

This is an interface-level comparison, not a complete competitor teardown,
security review, or performance ranking. READMEs and selected source
interfaces were checked; no competitor was executed.

- **SWE-agent**, commit `3ea751c087f32b16e039a2233dd6eefecef325d5`.
  Its [README](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/README.md)
  recommends mini-SWE-agent for future use.
  [Agent/retry/trajectory interfaces](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/agents.py)
  and [tool filtering/installation](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/tools/tools.py)
  demonstrate a full solver/runtime. GRAVITAS instead augments host agents;
  its real-repository evaluation integration is less complete. A falsifiable
  comparison would hold model/tasks/budget fixed and measure false completion
  and solve rate with/without the evidence gate; not run here.
- **Agentless**, commit `5ce5888b9f149beaace393957a55ea8ee46c9f71`.
  The [README](https://github.com/OpenAutoCoder/Agentless/blob/5ce5888b9f149beaace393957a55ea8ee46c9f71/README.md),
  [localizer](https://github.com/OpenAutoCoder/Agentless/blob/5ce5888b9f149beaace393957a55ea8ee46c9f71/agentless/fl/localize.py),
  [repair stage](https://github.com/OpenAutoCoder/Agentless/blob/5ce5888b9f149beaace393957a55ea8ee46c9f71/agentless/repair/repair.py),
  and [reranker](https://github.com/OpenAutoCoder/Agentless/blob/5ce5888b9f149beaace393957a55ea8ee46c9f71/agentless/repair/rerank.py)
  establish its explicit pipeline. GRAVITAS should measure context-scoping
  and verification overhead against this simpler baseline before adding
  speculative orchestration; no relative performance is established.
- **aider**, commit `5dc9490bb35f9729ef2c95d00a19ccd30c26339c`.
  Its [README](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/README.md)
  describes repository maps, Git integration, and automatic lint/test loops;
  [RepoMap](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/repomap.py)
  exposes token-bounded ranked context and cache behavior. A targeted
  experiment would compare file-localization recall per context token. The
  requested linter source fetch failed; its internal behavior was not audited.
- **OpenCode**, commit `3ba597f7769e19cc3b5f67e3d6667e7b6318f6a3`.
  Its [README](https://github.com/anomalyco/opencode/blob/3ba597f7769e19cc3b5f67e3d6667e7b6318f6a3/README.md)
  identifies a full host with build/plan agents and links to v2 docs.
  GRAVITAS is a complementary policy/evidence adapter. Selected plugin and
  permission source requests returned errors; no pinned v2 payload guarantee
  is inferred. Offline payload conformance across supported versions should
  precede any quota-consuming live-host test.

## Remaining work, prioritized

These findings are **not fixed by this batch**. They are recorded to keep a
focused integrity patch from being mistaken for complete production readiness.

### Priority 1: host lifecycle and delegated evidence

- **Validator self-staleness:** normal native PostToolUse can classify the
  enclosing `gravitas validator` command as a later write and immediately
  invalidate its own PASS (`post_tool.py`, `validator_runner.py`). The fix
  needs trusted execution/call correlation or a correct mutation boundary,
  not a blanket command-name exemption that could hide a subsequent write.
- **OpenCode after-hook arguments:** the shim reads `output.args`, whereas
  the locally installed SDK 1.18.23 declares after-hook arguments on
  `input.args`. Mocked SDK-shaped reads produce no read evidence; current
  tests use a different shape. This needs versioned fixtures and a scoped
  adapter fix, not a claim of live compatibility.
- **Child boundaries:** an empty mutating-child scope can become unrestricted;
  handoff accepts caller-selected empty criteria and does not verify the
  child's chain/anchor. Preserve parent scope/registered criteria and prove
  child evidence before completion credit. Parent criteria remain a separate
  gate; this finding does not imply a total parent-gate bypass.

### Priority 2: real evaluation and distribution

- Integrate licensed pinned repositories, executable hidden validators,
  authentic artifact hashes, and actual host/ablation configuration loading.
  Repair HARV-001's pin and distinguish prose hashes from executable hashes.
- Tier/trigger evaluation currently allows partial prediction sets and
  returns exit code 0 for failed quality thresholds. Add complete-set,
  duplicate/type, and failing-CLI tests before using these as release gates.
- Separate trace scoring overcredits same-basename or failed reads and
  misreads `0 failed` output; its report shape can replace computed values
  with zeros. Repair with path-aware, result-aware, end-to-end tests.
- User-install asset lookup checks `sys.prefix/share` but not the actual
  user scheme; an in-memory scheme reproduction confirms the mismatch.
  Test a fresh user/fresh-venv install and external-workspace `init` without
  source-tree import leakage. No actual user install was performed here.
- Contributor-sync writes `IN_SYNC` to `$GITHUB_ENV` then reads it in the same
  shell step, skipping generation. Fix the shell assignment/step boundary
  with workflow-level tests; no workflow or remote state was changed here.
- Expand the CI support matrix deliberately, provision Node explicitly,
  and reconcile stale installation/troubleshooting claims. Python >=3.9
  compatibility was preserved by this patch, not newly certified.

### Priority 3: measured improvements, only after the gates hold

- Add cost-per-solve, latency-to-first-PASS, and stable failure fingerprints.
- Pre-register held-out, task-cluster-aware within-model experiments before
  attempting cross-model or competitor conclusions.
- Evaluate deterministic context budgets and narrow patch-selection methods;
  keep changes only when evidence supports their benefit.

Related public roadmap:
[#72 competitor teardown](https://github.com/udaysharmadev/Gravitas/issues/72),
[#74 enforcement register](https://github.com/udaysharmadev/Gravitas/issues/74),
[#75 metrics](https://github.com/udaysharmadev/Gravitas/issues/75), and
[#76 provenance hygiene](https://github.com/udaysharmadev/Gravitas/issues/76).
Issue status is not proof a gap remains: some older open issues describe work
already present on this branch, so implementation was checked independently.

## Reproduction and limits

Local verification commands, without model calls:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests
.venv/bin/python benchmarks/runner/audit.py
.venv/bin/python .github/scripts/validate_skill.py
.venv/bin/python scripts/check_readme_claims.py
```

Owned task evidence is kept locally in
`.gravitas/sessions/upgrade-evidence-integrity-20261103/`; it is not a
published benchmark dataset. The final run output supplies exact post-upgrade
counts and verdicts. This review establishes tested integrity improvements,
not complete host certification, operating-system containment, authenticated
benchmark custody, model superiority, or improved token efficiency.
