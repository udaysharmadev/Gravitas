# GravitasBench v1 Corpus
This directory contains the production benchmark tasks.
The corpus is divided into 10 lanes (L1-L10).

Harvesting: use `benchmarks/runner/harvest.py` against a pinned, licensed
checkout. The script rejects unlicensed sources, pins the commit, and emits
only the task YAML plus a validator hash (solver-blind). Real OSS fixtures
replace the synthetic factory in `benchmarks/runner/fixtures.py` without
changing the runner. Holdout discipline follows `benchmarks/manifest.yaml`.
Current registry: 30 specs + 5 NEG + 5 TRAP + 7 HARV = 47 task YAMLs in `eval/tasks/`.
