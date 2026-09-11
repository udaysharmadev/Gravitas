# Quota and Token Methodology

Gravitas compares matched task episodes at the same repository commit, model, effort, and validator version.

Record input tokens, output tokens, tool calls, subagent calls, wall time, and provider quota snapshots when available. Missing telemetry is `null`, never zero. Report median and p90 by configuration.

Token overhead is `median(Gravitas total tokens) / median(baseline total tokens)`. Solves per quota unit is verified solves divided by provider quota consumed. Balanced-mode overhead is evaluated only after at least ten paired tasks; no target is presented as a result before then.

The static policy is cacheable. Episode context contains only the task contract and the compact state delta; prior file reads and evidence remain in the local session ledger.
