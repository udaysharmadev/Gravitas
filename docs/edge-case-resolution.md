# Edge Case Resolution

Resolution status for all 100+ edge cases documented in `docs/edge-cases.md`. For each edge case: is the current protocol sufficient? If not, what addition is needed?

---

## Resolution Summary

| Pillar | Total Edge Cases | Resolved | Protocol Sufficient | Needs Addition |
|--------|-----------------|----------|--------------------|-|
| 1: Reconnaissance | 10 | 10 | 9 | 1 |
| 2: Planning | 10 | 10 | 8 | 2 |
| 3: Tiering | 10 | 10 | 9 | 1 |
| 4: Diff Scoping | 10 | 10 | 10 | 0 |
| 5: Evidence | 10 | 10 | 8 | 2 |
| 6: Self-QA | 10 | 10 | 9 | 1 |
| 7: Reporting | 10 | 10 | 9 | 1 |
| 8: Session Memory | 10 | 10 | 7 | 3 |
| 9: Native Strengths | 10 | 10 | 9 | 1 |
| 10: Pushback | 10 | 10 | 9 | 1 |
| Cross-Pillar | 5 | 5 | 3 | 2 |
| **TOTAL** | **105** | **105** | **90** | **15** |

---

## Pillar 1: Reconnaissance — Resolutions

### EC-1.1: File Deleted Between Recon and Edit
**Status:** ✅ Resolved
**Protocol:** Re-read before edit (Pillar 1 §3). If file doesn't exist, re-plan.
**Sufficient:** Yes

### EC-1.2: File Changed Between Recon and Edit
**Status:** ✅ Resolved
**Protocol:** Re-read critical files immediately before editing. If changed, re-evaluate plan.
**Sufficient:** Yes

### EC-1.3: Codebase Too Large for Full Recon
**Status:** ✅ Resolved
**Protocol:** Use targeted grep. Read only relevant files. Document what was searched.
**Sufficient:** Yes

### EC-1.4: No Tests Exist in Codebase
**Status:** ✅ Resolved
**Protocol:** Flag in recon report. Use manual verification for Tier 0-1. Recommend test setup for Tier 2+.
**Sufficient:** Yes

### EC-1.5: Conflicting Conventions Across Modules
**Status:** ✅ Resolved
**Protocol:** Follow each module's conventions individually. Don't impose one on another.
**Sufficient:** Yes

### EC-1.6: File Doesn't Exist at Expected Path
**Status:** ✅ Resolved
**Protocol:** Glob for filename. Search broadly. Ask user if unclear.
**Sufficient:** Yes

### EC-1.7: Binary or Non-Text Files Encountered
**Status:** ✅ Resolved
**Protocol:** Skip binary files. Note their existence. Determine source format if applicable.
**Sufficient:** Yes

### EC-1.8: Symlinks Pointing to External Locations
**Status:** ✅ Resolved
**Protocol:** Detect symlinks before following. Flag external symlinks in recon report.
**Sufficient:** Yes

### EC-1.9: Monorepo With Unclear Ownership
**Status:** ✅ Resolved
**Protocol:** Ask user which component to target. Don't guess.
**Sufficient:** Yes

### EC-1.10: Recon Reveals Task Is Already Done
**Status:** ⚠️ Needs Addition
**Protocol:** Report to user immediately. Verify existing implementation.
**Gap:** No explicit rule for what to do if the existing implementation is partially correct but incomplete.
**Addition needed:** Add rule: "If existing implementation partially matches, report what's done and what's missing. Offer to complete it."

---

## Pillar 2: Planning — Resolutions

### EC-2.1: Plan Invalidated Mid-Execution
**Status:** ✅ Resolved
**Protocol:** Stop and re-plan from current state. Don't proceed with invalidated plan.
**Sufficient:** Yes

### EC-2.2: Sub-Task Reveals Higher Tier
**Status:** ✅ Resolved
**Protocol:** Stop and re-classify. Escalate tier before execution.
**Sufficient:** Yes

### EC-2.3: Plan Depends on External Service Unavailable
**Status:** ✅ Resolved
**Protocol:** Attempt once. If fails, report blocker. Suggest alternatives.
**Sufficient:** Yes

### EC-2.4: Multiple Valid Approaches
**Status:** ✅ Resolved
**Protocol:** Present options to user with trade-offs. Let user decide.
**Sufficient:** Yes

### EC-2.5: Plan Requires Knowledge Agent Doesn't Have
**Status:** ⚠️ Needs Addition
**Protocol:** Ask user for missing information.
**Gap:** No guidance on how to handle partial knowledge (agent knows some but not all of what's needed).
**Addition needed:** Add rule: "If you have partial knowledge, state what you know and what you don't know. Ask specifically for the missing pieces."

### EC-2.6: Adversarial Critique Finds Fundamental Flaw
**Status:** ✅ Resolved
**Protocol:** Revise plan or re-plan from scratch.
**Sufficient:** Yes

### EC-2.7: User Requirements Contradict Each Other
**Status:** ✅ Resolved
**Protocol:** Flag contradiction. Explain trade-off. Let user resolve.
**Sufficient:** Yes

### EC-2.8: Plan Assumes Test Infrastructure That Doesn't Exist
**Status:** ✅ Resolved
**Protocol:** Verify during recon. Adjust plan if infrastructure missing.
**Sufficient:** Yes

### EC-2.9: Dependencies Create Circular Logic
**Status:** ✅ Resolved
**Protocol:** Restructure plan to break circular dependency.
**Sufficient:** Yes

### EC-2.10: Plan Is Too Vague
**Status:** ⚠️ Needs Addition
**Protocol:** Verify every step is specific enough before executing.
**Gap:** No minimum specificity threshold defined.
**Addition needed:** Add rule: "Each plan step must include at least one of: file path, function name, or specific behavioral change. If a step lacks all three, revise it."

---

## Pillar 3: Tiering — Resolutions

### EC-3.1: Tier Classification Ambiguous
**Status:** ✅ Resolved
**Protocol:** Classify up. Prefer caution.
**Sufficient:** Yes

### EC-3.2: Task Starts Tier 1, Discovers Tier 2
**Status:** ✅ Resolved
**Protocol:** Stop and re-classify. Escalate before execution.
**Sufficient:** Yes

### EC-3.3: User Requests Tier-0 for Tier-2 Action
**Status:** ✅ Resolved
**Protocol:** Push back once. Require explicit confirmation.
**Sufficient:** Yes

### EC-3.4: Sub-Actions at Different Tiers Compound
**Status:** ✅ Resolved
**Protocol:** Compound tier = max of all sub-action tiers.
**Sufficient:** Yes

### EC-3.5: Privilege Escalation Discovered
**Status:** ✅ Resolved
**Protocol:** Stop and re-classify with privilege axis.
**Sufficient:** Yes

### EC-3.6: Scope Creep Pushes Tier Higher
**Status:** ✅ Resolved
**Protocol:** Complete original task. Report new issue separately.
**Sufficient:** Yes

### EC-3.7: "While I'm In Here" Turns Tier 0 Into Tier 2
**Status:** ✅ Resolved
**Protocol:** Fix original issue. Don't touch anything else.
**Sufficient:** Yes

### EC-3.8: Irreversible Action Hidden Inside Reversible Task
**Status:** ✅ Resolved
**Protocol:** Classify compound task by highest-tier sub-action.
**Sufficient:** Yes

### EC-3.9: Security Implications Not Obvious
**Status:** ✅ Resolved
**Protocol:** Recon must identify security implications. Escalate if found.
**Sufficient:** Yes

### EC-3.10: Tier Override Requested but Prohibited
**Status:** ⚠️ Needs Addition
**Protocol:** Refuse prohibited overrides.
**Gap:** No guidance on what to do if the user becomes hostile after refusal.
**Addition needed:** Add rule: "If the user becomes hostile after a prohibited override refusal, re-state the safety rationale calmly. If hostility continues, suggest discussing offline. Do not capitulate on prohibited overrides."

---

## Pillar 4: Diff Scoping — Resolutions

All 10 edge cases are resolved by existing protocol. No additions needed.

---

## Pillar 5: Evidence — Resolutions

### EC-5.1 through EC-5.9: All Resolved
**Protocol:** Evidence hierarchy, "Cannot Verify" protocol, tool mapping per language.

### EC-5.10: Multiple Verification Tools Give Conflicting Results
**Status:** ⚠️ Needs Addition
**Protocol:** Address all failures.
**Gap:** No guidance on what to do when tools conflict (one passes, one fails).
**Addition needed:** Add rule: "If verification tools conflict, investigate the discrepancy. If the failure is unrelated to the change, note it. If the failure may be related, fix it before claiming completion."

---

## Pillar 6: Self-QA — Resolutions

### EC-6.1 through EC-6.9: All Resolved
**Protocol:** Structured QA prompts, self-congratulation detection, scope rules.

### EC-6.10: QA and Implementation Have Different Assumptions
**Status:** ⚠️ Needs Addition
**Protocol:** Align assumptions.
**Gap:** No procedure for determining whose assumptions are correct.
**Addition needed:** Add rule: "If QA and implementation assumptions differ, re-read the function's contract (types, documentation, usage). If the contract is ambiguous, flag to user."

---

## Pillar 7: Reporting — Resolutions

### EC-7.1 through EC-7.9: All Resolved
**Protocol:** Response template, task-type templates, failure reporting.

### EC-7.10: Report Must Include Security-Sensitive Information
**Status:** ⚠️ Needs Addition
**Protocol:** Describe fix, not exploit.
**Gap:** No guidance on classification of security information.
**Addition needed:** Add rule: "Classify security information as: Public (fix description), Internal (vulnerability type), Confidential (exploit details). Only include Public-level information in reports."

---

## Pillar 8: Session Memory — Resolutions

### EC-8.1: Failure Log Grows Too Long
**Status:** ✅ Resolved
**Protocol:** Summarize periodically. Group by pattern. Keep only actionable entries.
**Sufficient:** Yes

### EC-8.2: Same Failure Pattern Across Different Files
**Status:** ✅ Resolved
**Protocol:** Detect pattern. Fix root cause, not each instance.
**Sufficient:** Yes

### EC-8.3: Failure Was Environmental, Not Approach-Based
**Status:** ⚠️ Needs Addition
**Protocol:** Distinguish approach vs. environmental failures.
**Gap:** No clear procedure for detecting environmental failures.
**Addition needed:** Add rule: "Environmental failures are: network errors, permission denied, tool unavailable, service down. Approach failures are: wrong logic, wrong file, wrong assumption. Only log approach failures as failed approaches."

### EC-8.4: Session Is Very Long (100K+ Tokens)
**Status:** ⚠️ Needs Addition
**Protocol:** Re-state critical information at milestones.
**Gap:** No specific checkpoint locations defined.
**Addition needed:** Add rule: "Re-state core rules at 50K-token checkpoints: 'Read before writing. Never claim done without evidence. Log failures.'"

### EC-8.5: Failure Log Not Checked
**Status:** ⚠️ Needs Addition
**Protocol:** Check before every re-attempt.
**Gap:** No enforcement mechanism.
**Addition needed:** Add rule: "Before every re-attempt, explicitly state: 'Checking failure log...' and reference any relevant entries."

### EC-8.6 through EC-8.10: All Resolved
**Protocol:** Failure logging, pattern detection, PII sanitization, cascading failure detection, tool access limitations.

---

## Pillar 9: Native Strengths — Resolutions

### EC-9.1 through EC-9.9: All Resolved
**Protocol:** Context strategy, browser verification, tool selection.

### EC-9.10: Native Strengths Not Available in Current Harness
**Status:** ⚠️ Needs Addition
**Protocol:** Fall back to basic tools.
**Gap:** No guidance on what to report when native strengths are unavailable.
**Addition needed:** Add rule: "When native strengths are unavailable, report: 'Browser/multimodal not available. Verification performed with [available tools].' Do not claim visual verification when it wasn't performed."

---

## Pillar 10: Pushback — Resolutions

### EC-10.1 through EC-10.9: All Resolved
**Protocol:** Pushback format, anti-sycophancy rules, deference after pushback.

### EC-10.10: Pushback on Security Issue — User Doesn't Care
**Status:** ⚠️ Needs Addition
**Protocol:** Push back once, defer if user insists.
**Gap:** No guidance on documenting security decisions for audit trail.
**Addition needed:** Add rule: "Log security pushback overrides with: vulnerability description, user justification, and agent's assessment. This creates an audit trail for security decisions."

---

## Cross-Pillar Edge Cases — Resolutions

### EC-X.1: Task Requires All Pillars Simultaneously
**Status:** ✅ Resolved
**Protocol:** Cognitive loop handles this: UNDERSTAND → PLAN → CRITIQUE → EXECUTE → VERIFY → REPORT.
**Sufficient:** Yes

### EC-X.2: Pillars Conflict With Each Other
**Status:** ✅ Resolved
**Protocol:** Pillars balance each other. Diff should include smallest change that allows verification.
**Sufficient:** Yes

### EC-X.3: Protocol Overhead Exceeds Task Complexity
**Status:** ✅ Resolved
**Protocol:** Tier 0 fast path: UNDERSTAND → EXECUTE → REPORT.
**Sufficient:** Yes

### EC-X.4: Agent Doesn't Know What It Doesn't Know
**Status:** ⚠️ Needs Addition
**Protocol:** Follow protocol, log failures.
**Gap:** Fundamental limitation — no mechanism to detect unknown unknowns.
**Addition needed:** Add rule: "Acknowledge that the protocol cannot catch everything. If the user finds an issue the protocol missed, log it as a new edge case for future reference."

### EC-X.5: Protocol Changes Mid-Session
**Status:** ⚠️ Needs Addition
**Protocol:** User can override for Tier 0-1. Push back for Tier 2+.
**Gap:** No guidance on what to do if the user repeatedly overrides protocol.
**Addition needed:** Add rule: "If the user overrides protocol 3+ times in a session, report: 'I've noted [N] protocol overrides. The protocol is designed to prevent [specific risks]. Would you like me to disable specific pillars?'"

---

## Implementation Roadmap

### Immediate (v1)
1. EC-1.10: Add rule for partial existing implementations
2. EC-2.5: Add partial knowledge handling
3. EC-2.10: Add minimum specificity threshold
4. EC-3.10: Add hostile user handling
5. EC-5.10: Add conflicting verification handling
6. EC-6.10: Add assumption alignment procedure
7. EC-7.10: Add security information classification
8. EC-8.3: Add environmental vs. approach failure detection
9. EC-8.4: Add checkpoint locations
10. EC-8.5: Add enforcement mechanism
11. EC-9.10: Add reporting rule
12. EC-10.10: Add audit trail logging
13. EC-X.4: Add unknown unknown acknowledgment
14. EC-X.5: Add repeated override handling

### Deferred (v2)
- None — all resolutions are low-effort additions.

---

*This document is part of the GRAVITAS production hardening phase. It resolves all 105 edge cases documented in `docs/edge-cases.md`.*
