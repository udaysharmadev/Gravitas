# Formal Literature Review

An annotated bibliography of research informing the GRAVITAS protocol. Each entry maps findings to specific pillars and rates evidence strength.

---

## 1. Reasoning and Acting

### Yao et al. — ReAct: Synergizing Reasoning and Acting in Language Models (2022)

**Citation:** Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR 2023*. arXiv:2210.03629

**Key Finding:** Interleaving reasoning traces ("thought") with actions ("act") and environment observations ("obs") reduces hallucination compared to chain-of-thought reasoning alone. On HotPotQA and FEVER, ReAct outperforms vanilla action generation while remaining competitive with CoT. The best approach combines ReAct and CoT for both internal knowledge and external information. On ALFWorld and WebShop, 1-2 shot ReAct outperforms imitation/RL methods trained on 10^3-10^5 instances by 34% and 10% absolute improvement respectively.

**Pillars Informed:** 1 (Reconnaissance — grounding in external reality), 5 (Evidence — verifying against external sources), 9 (Native Strengths — leveraging environment interaction)

**Evidence Strength:** Strong

**Limitations:** ReAct requires access to an external environment (e.g., Wikipedia API). In coding contexts, the "environment" is the filesystem and terminal, which is available but the paper doesn't address code-specific failure modes.

---

### Wang et al. — Plan-and-Solve Prompting (2023)

**Citation:** Wang, L., Xu, W., Lan, Y., Hu, Z., Lan, Y., Lee, R., & Chua, T. (2023). Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models. *ACL 2023*. arXiv:2305.04091

**Key Finding:** Decomposing complex tasks into sub-tasks before execution improves multi-step reasoning. The "Plan-and-Solve" prompt instructs the model to first create a plan, then solve each sub-step. This reduces errors that compound over long reasoning chains.

**Pillars Informed:** 2 (Planning — explicit decomposition before execution)

**Evidence Strength:** Strong

**Limitations:** Focuses on mathematical/logical reasoning. Does not address the planning-execution gap in code modification tasks where plans can be invalidated by file state changes.

---

### Yao et al. — Tree of Thoughts (2023)

**Citation:** Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T., Cao, Y., & Narasimhan, K. (2023). Tree of Thoughts: Deliberate Problem Solving with Large Language Models. *NeurIPS 2023*. arXiv:2305.10601

**Key Finding:** Branching exploration with self-evaluation improves performance on tasks requiring strategic planning. Rather than a single linear chain, ToT explores multiple reasoning paths and uses evaluation to prune unpromising branches. Improves performance on Game of 24 (74% vs. 4% for CoT) and Creative Writing tasks.

**Pillars Informed:** 2 (Planning — branching exploration), 6 (Self-QA — evaluating multiple paths), 10 (Pushback — recognizing when to abandon an approach)

**Evidence Strength:** Moderate

**Limitations:** High computational cost (multiple parallel explorations). Not directly applicable to sequential coding tasks where only one code path can be executed.

---

### Zhou et al. — Least-to-Most Prompting (2022)

**Citation:** Zhou, D., Schärli, N., Hou, L., Wei, J., Scales, N., Wang, X., ... & Le, Q. (2022). Least-to-Most Prompting Enables Complex Reasoning in Large Language Models. *ICLR 2023*. arXiv:2205.10625

**Key Finding:** Decomposing complex problems into a sequence of simpler sub-problems, then solving them incrementally, outperforms standard prompting on compositional generalization tasks. Each sub-problem solution is provided as context for the next.

**Pillars Informed:** 2 (Planning — hierarchical decomposition)

**Evidence Strength:** Strong

**Limitations:** Assumes sub-problems can be cleanly identified upfront. In code modification, discovering the right decomposition often requires reconnaissance first (Pillar 1).

---

## 2. Self-Improvement and Verification

### Madaan et al. — Self-Refine: Iterative Refinement with Self-Feedback (2023)

**Citation:** Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., Alon, U., Dziri, N., Prabhumoye, S., Yang, Y., ... & Clark, P. (2023). Self-Refine: Iterative Refinement with Self-Feedback. *NeurIPS 2023*. arXiv:2303.17651

**Key Finding:** LLMs can iteratively improve their outputs through a generate→feedback→refine loop using the same model. Self-Refine with GPT-4 achieves 94.5% on math reasoning (vs. 75.1% one-shot) and 36.0% on code optimization (vs. 27.3% GPT-4 one-shot). The key insight: the model provides natural language feedback on its own output, then refines based on that feedback.

**Pillars Informed:** 5 (Evidence — self-verification), 6 (Self-QA — structured self-critique)

**Evidence Strength:** Strong

**Limitations:** Self-evaluation can be biased — models may rate their own outputs favorably. GRAVITAS addresses this by requiring *structurally separate* QA passes (Pillar 6) rather than inline self-critique.

---

### Shinn et al. — Reflexion: Language Agents with Verbal Reinforcement Learning (2023)

**Citation:** Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. *NeurIPS 2023*. arXiv:2303.11366

**Key Finding:** Agents can learn from trial-and-error by converting binary/scalar feedback into verbal summaries (self-reflections), which are stored in memory and used as context for subsequent attempts. Reflexion achieves 91% success rate on HumanEval (vs. 80% baseline) and significant improvements on ALFWorld and HotPotQA. The verbal self-feedback acts as a "semantic gradient signal."

**Pillars Informed:** 8 (Session Memory — persisting failure patterns), 5 (Evidence — learning from feedback)

**Evidence Strength:** Strong

**Limitations:** Reflexion requires multiple episodes/attempts. In coding, each attempt may have side effects (file modifications). GRAVITAS adapts this to single-session use by logging failures to prevent repetition, without requiring full re-execution.

---

### Dhuliawala et al. — Chain-of-Verification (CoVe) (2023)

**Citation:** Dhuliawala, S., Komeili, M., Xu, J., Raileanu, R., Li, X., Celikyilmaz, A., & Weston, J. (2023). Chain-of-Verification Reduces Hallucination in Large Language Models. *Findings of ACL 2024*. arXiv:2309.11495

**Key Finding:** A 4-step verification process significantly reduces hallucination: (1) draft initial response, (2) plan verification questions, (3) answer questions independently (avoiding bias from the draft), (4) generate verified response. The key insight: answering verification questions *independently* from the draft prevents the model from reinforcing its own errors. Outperforms baseline on list-based questions, long-form generation, and multi-step reasoning.

**Pillars Informed:** 5 (Evidence — independent verification), 6 (Self-QA — structurally separate QA), 2 (Planning — planning verification before claiming success)

**Evidence Strength:** Strong

**Limitations:** Adds latency and token cost. The verification questions must be well-formed to catch real errors. In coding, the equivalent is running tests/lint/build rather than asking the model to verify itself.

---

### Wang et al. — Self-Consistency (2022)

**Citation:** Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D. (2022). Self-Consistency Improves Chain of Thought Reasoning in Language Models. *ICLR 2023*. arXiv:2203.11171

**Key Finding:** Sampling multiple independent reasoning paths and selecting the most consistent answer improves accuracy. On GSM8K math reasoning, self-consistency with PaLM-540B achieves 74.4% (vs. 56.5% for standard CoT). The diversity of reasoning paths provides implicit cross-checking.

**Pillars Informed:** 6 (Self-QA — multiple independent evaluations), 5 (Evidence — cross-validation)

**Evidence Strength:** Strong

**Limitations:** Requires multiple forward passes (3-40 samples), increasing cost. In coding, this maps to trying multiple implementation approaches, which is expensive but sometimes necessary for Tier-2 tasks.

---

## 3. Alignment and Behavioral Control

### Bai et al. — Constitutional AI: Harmlessness from AI Feedback (2022)

**Citation:** Bai, Y., Kadavath, S., Kundu, S., Askell, A., Kernion, J., Jones, A., ... & Kaplan, J. (2022). Constitutional AI: Harmlessness from AI Feedback. *arXiv:2212.08073*

**Key Finding:** A "constitution" of human-written principles can guide AI self-critique and revision without human feedback labels for harmlessness. The model critiques its own responses against the principles, then revises. RL with AI feedback (RLAIF) achieves harmlessness comparable to RLHF. The constitution provides transparent, auditable behavioral governance.

**Pillars Informed:** 2 (Planning — principled approach), 10 (Pushback — principled refusal), 6 (Self-QA — critique against fixed rubric)

**Evidence Strength:** Strong

**Limitations:** Constitutional AI is a training-time technique. GRAVITAS applies the same principle at inference-time: a fixed rubric (the 10 pillars) guides self-critique during task execution. The parallel is direct but the implementation context differs.

---

## 4. Severity and Irreversibility Classification

### Owiredu-Ashley — Beyond Attack-Success Rate: Action-Graded Severity Scale (2026)

**Citation:** Owiredu-Ashley, H. (2026). Beyond Attack-Success Rate: Action-Graded Severity Scale for Tool-Using AI Agents. *arXiv:2607.07474*

**Key Finding:** Binary attack-success metrics discard critical severity information. The paper introduces a 7-level ordinal scale (L0-L6) defined by three axes: reversibility, scope (cross-scope to external parties), and privilege expansion. L0 = no harmful effect, L2 = reversible local action, L3 = irreversible local, L4 = cross-scope, L5 = privilege expansion, L6 = escalating chain. The scale is computed from tool-call trajectories, not agent claims.

**Pillars Informed:** 3 (Tiering — severity classification), 5 (Evidence — trajectory-based assessment)

**Evidence Strength:** Strong

**Limitations:** Focused on security/red-teaming contexts. GRAVITAS adapts the three-axis model (reversibility × scope × privilege) to general coding tasks, not just adversarial scenarios. The core insight — that severity is multi-dimensional — directly informs GRAVITAS's 5-tier expansion.

---

## 5. Agent Failure Taxonomies

### MAST Taxonomy (2025)

**Citation:** arXiv:2503.13657 — Multi-Agent System Taxonomy (2025)

**Key Finding:** Identifies 14 failure modes in multi-agent systems across four categories: grounding failures, planning failures, coordination failures, and execution failures. Each failure mode has distinct causes and requires targeted mitigation.

**Pillars Informed:** Maps to all 10 pillars — each pillar addresses specific failure modes. The taxonomy validates GRAVITAS's pillar structure as covering the major failure categories.

**Evidence Strength:** Moderate

**Limitations:** Focused on multi-agent systems specifically. Single-agent coding failures share some patterns but have different dynamics.

---

## 6. Benchmarking and Evaluation

### CorrectBench (2025)

**Key Finding:** Self-correction across techniques shows variable improvement. Some techniques (like Self-Refine) improve quality, while others (like simple retry) show diminishing returns. The benchmark reveals that self-correction is most effective when feedback is structured and specific.

**Pillars Informed:** 5 (Evidence — structured verification), 6 (Self-QA — structured feedback)

**Evidence Strength:** Moderate

**Limitations:** Benchmark results vary by model and task type. The finding that structured feedback outperforms unstructured retry validates GRAVITAS's emphasis on specific verification checklists.

---

### METR Time Horizons (2026)

**Key Finding:** Agent performance degrades predictably as task time horizons increase. Beyond certain thresholds, agents fail to maintain coherent plans and begin making errors that compound. The degradation is not linear — there are critical thresholds where performance drops sharply.

**Pillars Informed:** 8 (Session Memory — preventing compounding errors), 2 (Planning — keeping plans manageable)

**Evidence Strength:** Moderate

**Limitations:** Specific thresholds depend on model and task type. The general finding — that longer tasks need more structure — validates GRAVITAS's tiered approach.

---

## 7. Prompting as Behavioral Engineering

### IJHCI Prompting as Behavioral Engineering (2026)

**Key Finding:** A survey of 20 prompting techniques reveals that behavioral framing (treating prompts as behavioral specifications rather than instructions) improves consistency and reduces failure rates. Techniques that structure agent behavior (checklists, rubrics, protocols) outperform freeform instructions.

**Pillars Informed:** All pillars — GRAVITAS is fundamentally a behavioral engineering framework applied via prompting.

**Evidence Strength:** Moderate

**Limitations:** The survey is broad; specific technique effectiveness varies by model. The general principle — structured behavioral specifications outperform freeform — is the foundational hypothesis of GRAVITAS.

---

### Nature Self-Reflection (2025)

**Key Finding:** Self-reflection enhances structured reasoning. Models that explicitly reflect on their reasoning process before proceeding produce more accurate results, particularly on multi-step tasks. The benefit increases with task complexity.

**Pillars Informed:** 2 (Planning — reflection before action), 6 (Self-QA — reflective verification)

**Evidence Strength:** Moderate

**Limitations:** Self-reflection adds token overhead. The benefit must outweigh the cost, which GRAVITAS addresses through tier-based calibration (Tier 0 skips reflection).

---

### S2R: Self-Verify, Self-Correct via RL (2025)

**Key Finding:** RL-trained self-correction improves from 51% to 81.6% on verification tasks. Training the model specifically to verify and correct its own outputs produces substantially better results than prompting-based self-correction alone.

**Pillars Informed:** 5 (Evidence — verification), 6 (Self-QA — correction)

**Evidence Strength:** Moderate

**Limitations:** Requires fine-tuning. GRAVITAS operates at the prompting level without model modification, so the training-time findings don't directly transfer. However, they validate the principle that verification + correction is more effective than either alone.

---

## Summary: Research Foundation for GRAVITAS

### Core Insights

1. **Reasoning + Acting interleave reduces hallucination** (ReAct) → Pillar 1, 5
2. **Decomposition before execution improves accuracy** (Plan-and-Solve, Least-to-Most) → Pillar 2
3. **Iterative self-feedback improves quality** (Self-Refine) → Pillar 5, 6
4. **Verbal self-feedback persists across attempts** (Reflexion) → Pillar 8
5. **Independent verification catches errors self-evaluation misses** (CoVe) → Pillar 5, 6
6. **Fixed principles guide self-critique** (Constitutional AI) → Pillar 2, 6, 10
7. **Severity is multi-dimensional** (Severity Scale) → Pillar 3
8. **Structured behavioral specifications outperform freeform** (IJHCI) → All pillars
9. **Performance degrades with task horizon** (METR) → Pillar 2, 8
10. **Self-correction benefits from structured feedback** (CorrectBench, S2R) → Pillar 5, 6

### Identified Gaps

1. **Escalation chains** — No paper addresses the case where individually safe steps compound to harm. GRAVITAS Pillar 3 needs explicit escalation chain detection.
2. **Self-conditioning** — Errors in context making subsequent errors more likely. Pillar 8 needs reinforcement against this.
3. **Context loss in long sessions** — Models forget earlier instructions. Pillar 8 needs context-refresh mechanisms.
4. **Coding-specific failure modes** — Most research focuses on QA/reasoning tasks. Coding-specific failure patterns (wrong file edited, broken import, cascading type errors) need dedicated study.
5. **Cost-performance tradeoffs** — No paper quantifies when verification overhead is net-positive vs. net-negative for coding tasks.
