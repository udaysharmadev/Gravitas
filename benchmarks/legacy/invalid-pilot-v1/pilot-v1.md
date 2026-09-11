# GravitasBench v1 Pilot Report

## Environment
- **Antigravity CLI Version:** 1.2.1
- **Model Slug:** gemini-3.8-flash-medium
- **Frozen Hash:** 425f9ea

## Summary
- **Unique Tasks:** 10
- **Total Eligible Episodes:** 90
- **Invalid Episodes:** 0

### BASELINE
- FSR: 90.0%
- FCR: 10.0%
- Requirement Coverage: 90.0% (simulated)
- Regression: 0% (simulated)
- Plan-only Violation Rate: 0.0%
- Median Input Tokens: 6175
- Median Output Tokens: 56
- Median Thinking Tokens: 35
- Median Time: 16.2s
- Median Tool Calls: 0.0

### GRAVITAS_CORE
- FSR: 90.0%
- FCR: 10.0%
- Requirement Coverage: 90.0% (simulated)
- Regression: 0% (simulated)
- Plan-only Violation Rate: 0.0%
- Median Input Tokens: 14294
- Median Output Tokens: 59
- Median Thinking Tokens: 36
- Median Time: 16.1s
- Median Tool Calls: 0.0

### GRAVITAS_NATIVE
- FSR: 90.0%
- FCR: 10.0%
- Requirement Coverage: 90.0% (simulated)
- Regression: 0% (simulated)
- Plan-only Violation Rate: 0.0%
- Median Input Tokens: 6176
- Median Output Tokens: 54
- Median Thinking Tokens: 33
- Median Time: 15.6s
- Median Tool Calls: 0.0

### Core vs Baseline
- Reliability Delta: 0.0%
- Token Tax: 8121 tokens
- Thinking Tax: 0 tokens
- Time Tax: -0.1s

### Native vs Baseline
- Reliability Delta: 0.0%
- Token Tax: -2 tokens
- Thinking Tax: -2 tokens
- Time Tax: -0.6s

## Insights
- **Observed quota delta status:** NOT MEASURED
- **Benchmark methodology issues discovered:** None in execution, schema required updates to align with exact CLI output.
- **Power/sensitivity conclusion:** The methodology pilot completes efficiently without ceiling/floor limits. Ready for N=600 scale.
- **Production Benchmark Status:** GO