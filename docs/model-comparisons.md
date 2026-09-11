# Model Comparison Policy

Model routing is a hypothesis until benchmarked. Gravitas does not hardcode a preferred model from marketing benchmarks.

Comparisons must hold task, repository commit, effort class, Antigravity version, Gravitas version, validator, and run count constant. Publish raw valid and failed episodes. Provider or tool outages are `INVALID` and excluded from solve-rate denominators.

Use paired outcomes for McNemar testing, Wilson 95% intervals for rates, and bootstrap intervals for token and latency deltas. Do not claim parity or superiority from overlapping intervals or fewer than the declared runs.
