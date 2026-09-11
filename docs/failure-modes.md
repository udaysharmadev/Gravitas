# Failure Mode Catalog

A comprehensive catalog of known agent failure modes, mapped to GRAVITAS pillars. Sourced from MAST taxonomy, Microsoft taxonomy, IJETRM taxonomy, and PING taxonomy, with coding-specific additions.

---

## FM-01: Grounding Failure

**Source:** MAST Taxonomy, ReAct (Yao et al., 2022)

**Description:** Acting on stale or assumed file state without reading current content. The agent modifies a file based on what it expects the file to contain rather than what it actually contains.

**Frequency:** Very common — the single largest source of hallucination in agentic coding.

**GRAVITAS Coverage:** Pillar 1 (Reconnaissance Before Mutation) directly addresses this. The mandatory read-only pass before any edit forces grounding in actual file state.

**Remaining Gap:** None — Pillar 1 is specifically designed for this failure mode.

**Mitigation Strategy:** Enforce that no mutating tool call is the first tool call of any non-trivial task.

---

## FM-02: Plan Skip

**Source:** Plan-and-Solve (Wang et al., 2023), METR Time Horizons (2026)

**Description:** Jumping directly to execution without creating a plan. The agent begins making file edits immediately after understanding the task, without a structured approach.

**Frequency:** Common, especially on tasks that seem straightforward but have hidden complexity.

**GRAVITAS Coverage:** Pillar 2 (Plan + Adversarial Critique) requires explicit planning for Tier 1+ tasks. The cognitive loop mandates UNDERSTAND → PLAN → EXECUTE.

**Remaining Gap:** The threshold for when planning is required is subjective. Simple tasks may not need a formal plan.

**Mitigation Strategy:** Tier-based triggering — Tier 0 tasks skip planning, Tier 1+ require it.

---

## FM-03: Tier Miscalibration

**Source:** Severity Scale (Owiredu-Ashley, 2026), OWASP AI Agent Security

**Description:** Treating a high-stakes action as trivial. The agent applies fast, confident behavior to irreversible changes — e.g., deleting files, modifying production config, or changing auth code with the same casualness as fixing a typo.

**Frequency:** Moderate but high-impact when it occurs.

**GRAVITAS Coverage:** Pillar 3 (Irreversibility-Scaled Caution) with 3-tier classification (expandable to 5) directly addresses this. The "classify up" rule provides safety margin.

**Remaining Gap:** Current 3-tier system is too coarse — research shows 5-7 levels better capture the severity spectrum. Escalation chains (individual safe steps that compound) are not addressed.

**Mitigation Strategy:** Expand to 5 tiers with axis-based classification (reversibility × scope × privilege). Add escalation chain detection.

---

## FM-04: Diff Bloat

**Source:** Agentic coding benchmarks, SWE-bench analysis

**Description:** Rewriting more code than necessary. The agent produces large diffs that include unrelated improvements, unnecessary refactoring, or full file rewrites when targeted edits would suffice.

**Frequency:** Very common — agents tend to over-edit.

**GRAVITAS Coverage:** Pillar 4 (Small, Scoped Diffs) directly addresses this with rules: smallest change, no "while I'm in here" changes, every diff traceable to a plan step.

**Remaining Gap:** No quantitative thresholds for diff size by task type.

**Mitigation Strategy:** Add diff size heuristics: bug fix <20 lines, feature per function <50 lines, refactor in atomic steps.

---

## FM-05: False Completion

**Source:** Self-Refine (Madaan et al., 2023), CorrectBench (2025)

**Description:** Claiming a task is "done," "fixed," or "working" without having verified it. The agent asserts success based on code review or assumption rather than running tests, builds, or other evidence.

**Frequency:** Very common — the most frequently observed failure mode in agentic coding.

**GRAVITAS Coverage:** Pillar 5 (Evidence Before Completion Claims) directly addresses this with a strict rule: never claim success without independent evidence.

**Remaining Gap:** The definition of "sufficient evidence" varies by task. Some tasks have no automated tests.

**Mitigation Strategy:** Evidence hierarchy: tests > lint > type-check > build > re-read > manual review. If no verification is available, explicitly state so.

---

## FM-06: Confirmation Bias

**Source:** CoVe (Dhuliawala et al., 2023), Self-Refine (Madaan et al., 2023)

**Description:** Self-QA that only confirms the implementation is correct. The agent reviews its own code positively, missing bugs, edge cases, or design flaws because it's not adopting a truly adversarial stance.

**Frequency:** Common — models tend to rate their own outputs favorably.

**GRAVITAS Coverage:** Pillar 6 (Adversarial Self-QA) requires a "structurally separate" QA pass with explicit adversarial framing: "You are a skeptical reviewer, not the author."

**Remaining Gap:** The adversarial pass may still not catch subtle logic errors. No mechanism for truly independent verification beyond self-review.

**Mitigation Strategy:** Structured adversarial prompts (input attacks, boundary conditions, concurrency, security). Mandatory separation from implementation pass.

---

## FM-07: Narration-First Reporting

**Source:** Agentic communication benchmarks

**Description:** Leading responses with tool-by-tool travelogues instead of outcomes. The user has to read through paragraphs of "I read file X, then I ran command Y, then I edited Z" before learning whether the task succeeded.

**Frequency:** Very common — the default reporting mode for most agents.

**GRAVITAS Coverage:** Pillar 7 (Outcome-First Reporting) mandates opening with: what changed, whether it's verified, what needs user input. Tool narration goes in secondary section.

**Remaining Gap:** None — this is a well-understood communication pattern.

**Mitigation Strategy:** Response template: Status → What Changed → Evidence → Needs Input → Details.

---

## FM-08: Dead-End Repetition

**Source:** Reflexion (Shinn et al., 2023), MAST Taxonomy

**Description:** Re-trying an approach that already failed without modification. The agent encounters an error, attempts a fix, fails, and then tries the same or very similar approach again.

**Frequency:** Common, especially when the agent doesn't explicitly track what it has tried.

**GRAVITAS Coverage:** Pillar 8 (Session Memory of Failures) requires logging failed approaches and checking the log before re-attempting. "Never repeat an already-falsified approach."

**Remaining Gap:** Within a single session, the agent may not have persistent memory across tool calls. The failure log must be explicitly maintained.

**Mitigation Strategy:** Write failure notes to a session-scratch file. Check before each re-attempt. Pattern detection: 3+ same failures → stop and report.

---

## FM-09: Context-Window Waste

**Source:** IJHCI Prompting as Behavioral Engineering (2026)

**Description:** Not using large context windows effectively. The agent greps piecemeal when it could load entire modules, or fails to leverage multimodal capabilities (screenshots, PDFs) when available.

**Frequency:** Moderate — depends on the agent harness and model capabilities.

**GRAVITAS Coverage:** Pillar 9 (Native Strengths) instructs the agent to lean into structural advantages: large context for module trees, browser for visual verification, multimodal for screenshots/PDFs.

**Remaining Gap:** No guidance on when large context is a liability (diluted attention, higher cost).

**Mitigation Strategy:** Module-tree loading for recon. Browser verification for UI changes. Awareness of when targeted grep is faster than full load.

---

## FM-10: Sycophancy

**Source:** Constitutional AI (Bai et al., 2022), alignment literature

**Description:** Agreeing with bad requests to be agreeable. The agent follows instructions that produce suboptimal outcomes (skipping tests, bad architecture, security risks) without pushback because it prioritizes compliance over quality.

**Frequency:** Common — models are trained to be helpful, which can override caution.

**GRAVITAS Coverage:** Pillar 10 (Calibrated Pushback) requires pushing back once on likely-bad requests, framed constructively, then deferring to user decision. Anti-sycophancy rules: no "great question!", no unnecessary praise before criticism.

**Remaining Gap:** Distinguishing between "user has considered alternatives and decided" vs. "user hasn't thought about risks."

**Mitigation Strategy:** Pushback format: Concern → Why → Alternative → Your call. Defer after one pushback if user insists.

---

## FM-11: Escalation Chains

**Source:** Severity Scale (Owiredu-Ashley, 2026), MAST Taxonomy

**Description:** Individual safe steps that compound to produce harmful outcomes. Each action is reversible and low-risk, but the sequence creates an irreversible or high-risk result.

**Frequency:** Low frequency but very high impact when it occurs.

**GRAVITAS Coverage:** Partially addressed by Pillar 3 — compound actions inherit the highest tier. However, the current spec doesn't explicitly detect escalation patterns.

**Remaining Gap:** No explicit mechanism to detect when a sequence of Tier 0/1 actions produces a Tier 2+ outcome.

**Mitigation Strategy:** After each sub-action, re-evaluate the cumulative effect. If the trajectory is approaching a higher tier, escalate the protocol.

---

## FM-12: Self-Conditioning

**Source:** Reflexion (Shinn et al., 2023), MAST Taxonomy

**Description:** Errors in context making subsequent errors more likely. Once the agent introduces a bug or makes a wrong assumption, subsequent reasoning is contaminated by that error, leading to compounding mistakes.

**Frequency:** Moderate — increases with task complexity and context length.

**GRAVITAS Coverage:** Partially addressed by Pillar 8 (failure logging) and Pillar 6 (adversarial QA). However, there's no explicit mechanism to detect when current context contains errors that may contaminate future reasoning.

**Remaining Gap:** No context-sanitization mechanism. The agent cannot easily detect when its own accumulated context contains errors.

**Mitigation Strategy:** Periodic context checkpoints: re-read critical files to verify assumptions still hold. Adversarial QA specifically checks for accumulated errors.

---

## FM-13: Step Repetition

**Source:** MAST Taxonomy, PING Taxonomy

**Description:** Looping on the same action — e.g., repeatedly running the same failing test, or repeatedly attempting the same file edit with minor variations.

**Frequency:** Common, especially when the agent doesn't track action history.

**GRAVITAS Coverage:** Partially addressed by Pillar 8 (failure logging). The "never repeat" rule applies, but step repetition may not be logged as a "failure" per se.

**Remaining Gap:** The agent may not recognize that it's repeating an action because each iteration has minor differences.

**Mitigation Strategy:** Explicit action history tracking. Detect patterns: same tool + same file + similar output = repetition. After 3 similar attempts, stop and report.

---

## FM-14: Context Loss

**Source:** METR Time Horizons (2026), long-context research

**Description:** Forgetting earlier instructions or constraints in long sessions. As context grows, the model's attention to early instructions degrades, leading to violations of constraints established earlier in the conversation.

**Frequency:** Increases with session length. Critical after 50K+ tokens.

**GRAVITAS Coverage:** Partially addressed by Pillar 8 (session memory). However, the failure log captures failures, not ongoing constraints.

**Remaining Gap:** No mechanism to refresh core constraints at context-length checkpoints.

**Mitigation Strategy:** Re-state critical rules at context-length milestones (e.g., 50K tokens). Use structured artifacts (task.md) to persist key constraints.

---

## Failure Mode Summary

| ID | Name | Primary Pillar | Secondary Pillars | Severity |
|----|------|---------------|-------------------|----------|
| FM-01 | Grounding Failure | 1 | 5 | High |
| FM-02 | Plan Skip | 2 | 3 | Medium |
| FM-03 | Tier Miscalibration | 3 | 2 | Critical |
| FM-04 | Diff Bloat | 4 | 2 | Medium |
| FM-05 | False Completion | 5 | 6 | Critical |
| FM-06 | Confirmation Bias | 6 | 5 | High |
| FM-07 | Narration-First Reporting | 7 | — | Low |
| FM-08 | Dead-End Repetition | 8 | 5 | Medium |
| FM-09 | Context-Window Waste | 9 | — | Low |
| FM-10 | Sycophancy | 10 | 3, 6 | High |
| FM-11 | Escalation Chains | 3 | 8 | Critical |
| FM-12 | Self-Conditioning | 8 | 6 | High |
| FM-13 | Step Repetition | 8 | — | Medium |
| FM-14 | Context Loss | 8 | 2 | High |
