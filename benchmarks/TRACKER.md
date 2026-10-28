# Benchmark Results Tracker

> Research preview: no publishable comparison yet. Every entry below links a
> versioned raw artifact. Marketing numbers must derive from these rows.

| Date | Gravitas commit | Dataset commit | Configs | Paired n | FSR delta [95% CI] | McNemar p | Median tokens | Report |
|---|---|---|---|---|---|---|---|---|
| _no runs yet_ | — | — | — | — | — | — | — | — |

## How to add a row

```bash
.venv/bin/python benchmarks/runner/report.py --help  # render report.md + summary.csv
# Copy the paired-comparison line into the table above with commit SHAs.
# Raw episodes stay in benchmarks/results/ (git-ignored unless smoke).
# Only rows with paired n >= 30 are publication-ready.
```
