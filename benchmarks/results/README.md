# GravitasBench Results

Four non-sensitive smoke episodes are published in this directory so public CI
can validate the same artifact shape users receive. They verify runner plumbing,
not model performance, and must not be aggregated into a Gemini, Gravitas, or
Claude success-rate claim.

A result release must contain raw episode JSON, the manifest and repository commits, evaluator and Antigravity versions, runs per configuration, all failures, and the generated summary. Validate it with:

```bash
python benchmarks/runner/validate.py --episodes benchmarks/results
python benchmarks/runner/summarize.py --episodes benchmarks/results
```

Do not place credentials, private source, or personal data in episode trajectories.
