# Empirical Gap Analysis

A systematic comparison of what the research literature says vs. what GRAVITAS currently implements vs. what's missing. For each pillar: research basis, current spec, gaps, proposed additions, and evidence strength.

---

## Pillar 1: Reconnaissance Before Mutation

### Research Basis
- **ReAct (Yao et al., 2022):** Interleaving reasoning with environment interaction reduces hallucination. Grounding in actual file state prevents acting on stale assumptions.
- **METR Time Horizons (2026):** Agent performance degrades when operating on assumed vs. observed state. Recon before mutation is the single most impactful behavioral intervention.

### Current GRAVITAS Spec
- Mandatory read-only pass before any mutation.
- Convention detection procedure (naming, style, imports, tests, types).
- File-state verification (re-read before editing).
- Recon depth classification by tier (Tier 0: scan; Tier 1: target + related; Tier 2: full module tree).
- 4 worked examples (bug fix, feature, migration, refactor).

### What the Research Says We Should Also Do
1. **Dynamic recon depth adjustment.** Current spec uses fixed depth by tier. Research suggests recon depth should adapt based on codebase complexity and task uncertainty (Least-to-Most, Zhou et al., 2022).
2. **Cross-file dependency mapping.** Current recon identifies related files but doesn't explicitly map the dependency graph. Research shows dependency-aware recon reduces cascading errors.
3. **Git history recon.** Current spec mentions git history for Tier 2 but doesn't specify what to look for. Research suggests checking recent changes to the target area for context.

### Proposed v2 Addition
- Add "Dynamic Recon Depth" rule: if initial recon reveals unexpected complexity, deepen recon before proceeding.
- Add dependency graph construction for Tier 1+ tasks.
- Add git history check: `git log --oneline -10 -- [target file]` to understand recent changes.

### Evidence Strength
Moderate — supported by decomposition research but not specifically tested in coding agent contexts.

---

## Pillar 2: Plan + Adversarial Critique

### Research Basis
- **Plan-and-Solve (Wang et al., 2023):** Decomposition before execution improves multi-step tasks.
- **Self-Refine (Madaan et al., 2023):** Iterative self-critique improves output quality.
- **Tree of Thoughts (Yao et al., 2023):** Branching exploration with self-evaluation improves strategic planning.
- **Constitutional AI (Bai et al., 2022):** Fixed rubric self-critique shapes behavior.

### Current GRAVITAS Spec
- Two-step plan: Step A (produce plan), Step B (adversarial critique), Step C (revise).
- Plan format: numbered steps with files, risk, evidence, reversibility.
- Adversarial critique: 6 structured questions (blast radius, weakest assumption, worst case, boundary, critical steps, skeptic's view).
- Plan granularity by tier (Tier 0: think only; Tier 1: 2-5 steps; Tier 2: 5-15 steps).

### What the Research Says We Should Also Do
1. **Branching exploration.** Tree of Thoughts suggests exploring multiple plan alternatives before committing. Current spec produces one plan and critiques it. Research suggests producing 2-3 alternatives and selecting the best.
2. **Plan confidence scoring.** Current spec doesn't quantify plan confidence. Research suggests scoring each step's confidence to identify high-risk steps.
3. **Incremental replanning.** Current spec mentions replanning mid-execution but doesn't specify triggers. Research suggests explicit replanning triggers (new information, step failure, tier escalation).

### Proposed v2 Addition
- For Tier 2+ tasks: produce 2-3 plan alternatives, evaluate each, select the best.
- Add confidence scores to each plan step (high/medium/low).
- Add explicit replanning triggers: "Replan if [condition]."

### Evidence Strength
Strong — decomposition and self-critique are well-established. Branching is supported but has cost implications.

---

## Pillar 3: Irreversibility-Scaled Caution

### Research Basis
- **Severity Scale (Owiredu-Ashley, 2026):** L0-L6 irreversibility classification with 3-axis model (reversibility, scope, privilege).
- **NESHER Library (2026):** Irreversible action classifier with calibrated thresholds.
- **OWASP AI Agent Security:** Tiered governance for agent actions.
- **MindStudio Framework:** 4-tier classification system.

### Current GRAVITAS Spec
- 5-tier system (0-4) with axis-based classification (reversibility × scope × privilege).
- Decision tree for tier assignment.
- Escalation chain detection (cumulative tier calculation).
- Tier override rules (classify up if uncertain; user may override down with justification).
- Prohibited overrides for security/auth changes.
- 50+ worked examples across code edits, database, security, infrastructure, git, API, config.

### What the Research Says We Should Also Do
1. **Continuous tier assessment.** Current spec classifies once at the start. Research suggests re-classifying after each sub-action, especially when new information emerges.
2. **Probabilistic tier estimation.** Current spec uses deterministic classification. Research suggests incorporating uncertainty: "This is Tier 2 with 80% confidence; if the database has triggers, it's Tier 3."
3. **Historical tier calibration.** Current spec doesn't learn from past tier assignments. Research suggests tracking whether tier classifications were accurate and adjusting thresholds.

### Proposed v2 Addition
- Add mandatory re-classification after each sub-action for Tier 1+ tasks.
- Add confidence intervals to tier assignments.
- Add post-task tier accuracy tracking (was the tier correct?).

### Evidence Strength
Strong — the 5-tier system is well-supported by multiple frameworks. Continuous assessment is moderate.

---

## Pillar 4: Small, Scoped, Attributable Diffs

### Research Basis
- **SWE-bench Analysis:** Scoped edits outperform broad rewrites in agent comparisons.
- **Code Review Research:** Mixed functional + formatting diffs increase review time and reduce trust.
- **Refactoring Literature:** Atomic refactoring steps reduce regression risk.

### Current GRAVITAS Spec
- Diff size heuristics (bug fix <20 lines, feature <50 lines, config <10 lines, refactor <30 lines per step).
- Scope discipline rules ("while I'm in here," no mixed changes, import discipline, no opportunistic improvements).
- Diff attribution (every hunk maps to a plan step).
- When broader rewrites are appropriate (fundamentally broken code, >50% module change, explicit user request).
- 8 worked examples across TypeScript, Python, Rust, Go, SQL, React, YAML, tests.

### What the Research Says We Should Also Do
1. **Diff complexity scoring.** Current heuristics are line-count based. Research suggests also considering cyclomatic complexity, number of files touched, and dependency impact.
2. **Automated diff regression detection.** Current spec relies on human review for diff quality. Research suggests automated detection of common diff anti-patterns.
3. **Diff size prediction.** Current spec reacts to diff size after the fact. Research suggests predicting diff size during planning to adjust approach.

### Proposed v2 Addition
- Add complexity-weighted diff scoring (lines × files × dependency depth).
- Add automated diff anti-pattern detection (mixed changes, unattributable hunks).
- Add diff size prediction during planning.

### Evidence Strength
Moderate — scoped edits are well-established, but automated diff quality assessment is preliminary.

---

## Pillar 5: Evidence Before Completion Claims

### Research Basis
- **Self-Refine (Madaan et al., 2023):** Self-verification improves output quality but has bias blind spots.
- **CoVe (Dhuliawala et al., 2023):** Independent verification questions catch errors that self-evaluation misses.
- **CorrectBench (2025):** Self-correction benchmark shows models overestimate their own correctness.
- **S2R (2025):** RL-trained self-correction: 51% → 81.6% improvement.

### Current GRAVITAS Spec
- Evidence hierarchy: tests > type checks > lint > build > re-read > manual check.
- Evidence collection procedure: run verification after every edit.
- Verification tool mapping per language.
- "Cannot Verify" protocol for unavailable tools.
- Self-check questions before any completion claim.

### What the Research Says We Should Also Do
1. **Independent verification.** CoVe shows that answering verification questions independently (not from the implementation) catches more errors. Current spec runs verification tools but doesn't separate the verification reasoning from the implementation reasoning.
2. **Calibrated confidence.** Current spec doesn't quantify confidence in evidence. Research suggests: "Tests pass — high confidence" vs. "Re-read confirms — moderate confidence."
3. **Evidence provenance.** Current spec doesn't track when evidence was collected relative to edits. Stale evidence is a known failure mode.

### Proposed v2 Addition
- Add explicit separation: verify from the user's perspective, not the implementation perspective.
- Add confidence calibration to evidence (high/moderate/low based on evidence type).
- Add evidence timestamp tracking (when was verification last run relative to last edit).

### Evidence Strength
Strong — independent verification is well-established (CoVe). Calibrated confidence is moderate.

---

## Pillar 6: Adversarial Self-QA

### Research Basis
- **CoVe (Dhuliawala et al., 2023):** Independent verification questions catch errors self-evaluation misses.
- **Self-Refine (Madaan et al., 2023):** Iterative self-critique improves quality but has confirmation bias.
- **Chain-of-Thought Monitoring:** Models fail to recognize their own compounding errors.

### Current GRAVITAS Spec
- Structured QA prompts (input attacks, boundaries, state, security).
- Structurally separate QA pass ("skeptical reviewer, not author").
- QA depth by tier (Tier 0: 30s sanity; Tier 1: 2-5 min; Tier 2: full + adversarial).
- Self-congratulation detection (warning signs: "looks good" without specifics, happy-path only).

### What the Research Says We Should Also Do
1. **QA independence.** CoVe shows QA should be truly independent from implementation. Current spec frames it as "separate pass" but the same reasoning chain may still bias the QA.
2. **QA scope definition.** Current spec doesn't define what's in scope for QA. Research suggests scoping QA to the changed code and its immediate neighbors, not the entire codebase.
3. **QA failure escalation.** Current spec says "fix and re-run" but doesn't specify when to escalate QA failures to the user. Research suggests: QA failures that affect functionality should be escalated; cosmetic issues should be noted but not blocking.

### Proposed v2 Addition
- Add explicit QA independence: "Verify as if you are a user, not the implementer."
- Add QA scope rules: "QA covers [changed files] + [immediate neighbors]."
- Add QA failure escalation: functional failures block completion; cosmetic failures are noted.

### Evidence Strength
Strong — independent verification is well-established. Scope and escalation are moderate.

---

## Pillar 7: Outcome-First Reporting

### Research Basis
- **Agentic Communication Benchmarks:** Outcome-first reporting improves perceived quality.
- **Claude Sonnet 4.6:** "Report what actually happened, not what you intended." Evidence-based claims, failure-first reporting.
- **Communication Research:** Presentation quality affects trust independently of correctness.

### Current GRAVITAS Spec
- Response template: Status → What Changed → Verified → Needs Input → Details.
- Communication style rules: lead with outcomes, be specific, cite evidence, state uncertainty.
- Reporting by task type (bug fix, feature, refactor, config).
- When things go wrong: lead with failure, explicit inability to verify.
- Write style: one idea per sentence, 20 words, active verbs, no filler.

### What the Research Says We Should Also Do
1. **Adaptive report complexity.** Current spec has fixed templates. Research suggests adapting report length to task complexity (1 sentence for Tier 0, full template for Tier 2+).
2. **Report verification.** Current spec doesn't verify that reports match actual outcomes. Research suggests cross-checking report claims against evidence.
3. **Multi-audience reporting.** Current spec targets a single user. Research suggests adapting reports for different audiences (developer, manager, security reviewer).

### Proposed v2 Addition
- Add report complexity scaling by tier.
- Add report verification: "Does the report match the evidence?"
- Add audience-aware reporting when multiple stakeholders are involved.

### Evidence Strength
Moderate — outcome-first is well-established, but adaptive complexity and multi-audience are preliminary.

---

## Pillar 8: Session Memory of Failures

### Research Basis
- **Reflexion (Shinn et al., 2023):** Verbal self-feedback persisted across attempts improves performance.
- **MAST Taxonomy:** Self-conditioning and step repetition are recognized failure modes.
- **METR Time Horizons:** Context loss in long sessions degrades performance.

### Current GRAVITAS Spec
- Failure log format: attempt, result, root cause, "do not retry."
- When to log: test fails, build fails, user rejects, wrong result.
- When to check the log: before re-attempting, before new approach, at start of sub-task.
- Failure pattern detection: 3+ same failures → stop and report.
- Integration with Antigravity: use `task.md` Artifact.

### What the Research Says We Should Also Do
1. **Cross-session learning.** Current spec is single-session only. Research suggests persisting failure patterns across sessions (Reflexion's core insight).
2. **Failure categorization.** Current spec logs failures but doesn't categorize them. Research suggests categorizing by type (logic, environment, assumption, tool) to inform future approaches.
3. **Failure prediction.** Current spec reacts to failures. Research suggests predicting likely failures based on task characteristics and pre-empting them.

### Proposed v2 Addition
- Add cross-session failure persistence (store in project-level file).
- Add failure categorization (logic/environment/assumption/tool).
- Add failure prediction based on task type and codebase characteristics.

### Evidence Strength
Strong — Reflexion is well-established. Cross-session learning is moderate (privacy concerns).

---

## Pillar 9: Native Strengths

### Research Basis
- **IJHCI Prompting as Behavioral Engineering (2026):** 20 prompting techniques with latency/token profiles.
- **Large Context Research:** Context window utilization strategies affect performance.
- **Multimodal Research:** Visual verification improves UI task accuracy.

### Current GRAVITAS Spec
- Context window strategy: load entire modules vs. selective grep.
- Multimodal verification: browser screenshots, PDF/image reading.
- Browser as verification tool: before/after screenshots, DOM reading.
- Tool selection optimization: `read_many_files`, `codebase_search`, `grep_search`.
- When NOT to use native strengths (targeted grep faster, browser slower, large context dilutes).

### What the Research Says We Should Also Do
1. **Context utilization metrics.** Current spec doesn't measure how well context is being used. Research suggests tracking context utilization efficiency (relevant tokens / total tokens).
2. **Tool selection optimization.** Current spec provides guidance but doesn't optimize tool selection based on task characteristics. Research suggests selecting tools based on task type, codebase size, and available verification.
3. **Native strength cost-benefit.** Current spec recommends using native strengths but doesn't quantify the cost-benefit. Research suggests: "Use browser verification when the cost (time) is justified by the confidence gain."

### Proposed v2 Addition
- Add context utilization tracking.
- Add tool selection optimization rules based on task characteristics.
- Add cost-benefit analysis for native strength usage.

### Evidence Strength
Moderate — tool selection optimization is preliminary. Context utilization is emerging.

---

## Pillar 10: Calibrated Pushback

### Research Basis
- **Constitutional AI (Bai et al., 2022):** Fixed rubric self-critique shapes behavior.
- **Alignment Literature:** Sycophancy is a known failure mode across models.
- **Claude Sonnet 4.6:** "Never be sycophantic — honesty about limitations is more valuable than false confidence."

### Current GRAVITAS Spec
- Pushback decision criteria (when to push back, when NOT to).
- Pushback format: Concern → Why → Alternative → Your call.
- Anti-sycophancy rules: no "great question!", no unnecessary praise, direct and evidence-based.
- Calibrated uncertainty: "Confident because [evidence]," "Believe but can't verify [X]."
- Worked examples of appropriate pushback, deference, and calibrated uncertainty.

### What the Research Says We Should Also Do
1. **Pushback effectiveness tracking.** Current spec doesn't track whether pushbacks were correct. Research suggests tracking: "Was the pushback correct? Did the user's approach fail?"
2. **Pushback frequency calibration.** Current spec says "push back once" but doesn't calibrate frequency. Research suggests: too many pushbacks create friction; too few enable bad outcomes.
3. **Pushback framing optimization.** Current spec provides one framing format. Research suggests adapting framing based on user response patterns (some users respond to data, others to analogies).

### Proposed v2 Addition
- Add pushback effectiveness tracking (was the pushback correct?).
- Add pushback frequency calibration (target: 1 pushback per 10 tasks).
- Add adaptive pushback framing based on user response patterns.

### Evidence Strength
Moderate — anti-sycophancy is well-established, but effectiveness tracking and frequency calibration are preliminary.

---

## Cross-Pillar Gaps

### Gap 1: No Protocol for Protocol Failures

**What the research says:** Meta-reasoning research suggests agents should be able to detect when their own protocol is failing and adapt.

**Current GRAVITAS:** The protocol assumes the agent follows it correctly. There's no mechanism to detect when the protocol itself is producing bad outcomes.

**Proposed addition:** Add a meta-monitoring layer: "If the protocol is producing worse outcomes than no protocol, escalate to the user."

### Gap 2: No Multi-Session Learning

**What the research says:** Reflexion shows that persisting failure patterns across sessions improves performance. Current GRAVITAS is single-session only.

**Current GRAVITAS:** Failure log is session-scoped. Patterns are not persisted across sessions.

**Proposed addition:** Add project-level failure persistence (`GRAVITAS_FAILURES.md`) that survives session boundaries. Sanitize PII/secrets. Share anonymized patterns across users (Phase 7).

### Gap 3: No Adaptive Protocol Selection

**What the research says:** Not all pillars are equally valuable for all tasks. Research suggests adapting pillar emphasis based on task characteristics.

**Current GRAVITAS:** All pillars apply to all tasks (with tier-based scaling). No adaptation based on task type.

**Proposed addition:** Add task-type → pillar mapping: "For bug fixes, emphasize Pillars 1, 4, 5, 6. For refactors, emphasize Pillars 1, 4, 5. For security, emphasize Pillars 3, 6, 10."

### Gap 4: No Quantitative Cost-Benefit Analysis

**What the research says:** The cost of behavioral protocols (token overhead, time overhead) must be justified by the benefit (improved outcomes). No current analysis exists for GRAVITAS.

**Current GRAVITAS:** No measurement of token overhead, time overhead, or outcome improvement.

**Proposed addition:** Add measurement framework (Phase 5): track tokens per pillar, time per pillar, outcome improvement per pillar. Calculate break-even point.

### Gap 5: No Adversarial Robustness Testing

**What the research says:** Adversarial user input ("just say it works," "skip the planning") can degrade protocol adherence. No testing exists for GRAVITAS under adversarial conditions.

**Current GRAVITAS:** No adversarial robustness testing protocol.

**Proposed addition:** Add adversarial testing suite (Phase 5): test each pillar's resistance to adversarial user input. Measure degradation thresholds.

---

## Summary: Gap Priority Matrix

| Gap | Research Strength | Implementation Effort | Priority |
|-----|------------------|----------------------|----------|
| Cross-pillar gaps (meta-monitoring) | Moderate | High | Medium |
| Multi-session learning | Strong | High | High |
| Adaptive protocol selection | Moderate | Medium | Medium |
| Quantitative cost-benefit | Strong | High | High |
| Adversarial robustness | Strong | Medium | High |
| Continuous tier assessment | Strong | Low | High |
| Independent verification | Strong | Low | High |
| Branching plan exploration | Moderate | Medium | Medium |
| Diff complexity scoring | Moderate | Medium | Medium |
| Failure categorization | Strong | Low | High |
| Pushback effectiveness tracking | Moderate | Low | Medium |
| Report complexity scaling | Moderate | Low | Medium |

---

## Implementation Roadmap

### Phase 5 additions (Production Hardening):
1. Quantitative cost-benefit measurement framework.
2. Adversarial robustness testing suite.
3. Continuous tier assessment (re-classify after each sub-action).
4. Independent verification separation.
5. Failure categorization.
6. Pushback effectiveness tracking.

### Phase 7 additions (Advanced Research):
1. Cross-session failure persistence.
2. Adaptive protocol selection based on task type.
3. Branching plan exploration.
4. Meta-monitoring for protocol failures.
5. Context utilization metrics.
6. Diff complexity scoring.

---

*This analysis is part of the GRAVITAS protocol's research foundation. It informs the implementation roadmap and identifies areas where the protocol can be strengthened based on empirical evidence.*
