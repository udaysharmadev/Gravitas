# Validators (solver-blind metadata)

Each `<TASK_ID>.json` holds the hidden-validator **hash only**, never the
validator source. The solver worktree never contains acceptance tests;
`run_hidden_validation()` materializes them post-trajectory and records
only the sha256 in the episode (`hidden_validator_hash`).

Produced by `benchmarks/runner/harvest.py --out-dir`. Do not paste test
source here.
