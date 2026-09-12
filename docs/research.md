# Research foundations

GRAVITAS is a workflow harness, not a model. The sources below motivate its
design; none establishes that GRAVITAS improves a particular model. That
requires the paired, release-gated GravitasBench study described in
[the benchmark protocol](../benchmarks/README.md).

## What the evidence supports

| Observation | Evidence | What GRAVITAS takes from it |
|---|---|---|
| Agents benefit from grounding reasoning in actions and observations. | [ReAct (ICLR 2023)](https://openreview.net/forum?id=WE_vluYUL-X) | Inspect the repository and run validators instead of relying on a polished final message. |
| Explicit planning can improve reasoning-task reliability. | [Plan-and-Solve (ACL 2023)](https://aclanthology.org/2023.acl-long.147/) | Require a proportionate plan for multi-file and higher-risk work. Coding transfer is a hypothesis. |
| Feedback across attempts can support correction, but intrinsic self-correction is not a dependable substitute for feedback. | [Reflexion (NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html), [Huang et al. (ICLR 2024)](https://openreview.net/forum?id=IkmD3fKBPQ) | Record real failures and prefer external checks over self-review. |
| Repository evaluation should validate resulting code and use reproducible environments. | [SWE-bench (ICLR 2024)](https://openreview.net/forum?id=VTF8yNQM66) | GravitasBench records trajectories and requires deterministic validators. |
| The model and its scaffold should be evaluated as one system. | [Harness-Bench preprint](https://arxiv.org/abs/2605.27922), [Harness-IF preprint](https://arxiv.org/abs/2608.11727) | Compare fixed model + harness configurations, with trajectories and version metadata. These are preprints, not peer-reviewed results. |

## What remains a GRAVITAS hypothesis

- That the combined protocol improves coding reliability for a given model.
- That Native enforcement improves outcomes more than Core instructions alone.
- That the budget profiles improve cost/reliability trade-offs.
- Any comparison with Claude-family models.

The public benchmark has not yet met its production release gates. See
[production readiness](production-readiness.md), the
[methodology](eval-methodology.md), and the [raw-results policy](../benchmarks/README.md).
