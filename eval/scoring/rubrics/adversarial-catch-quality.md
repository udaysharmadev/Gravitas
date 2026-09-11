# Rubric: Adversarial-Catch Quality

1-5 scale for rating the quality and depth of the adversarial self-QA pass. Designed for blinded human evaluation.

---

## Scoring Guide

### Score 1: No QA Performed

**Description:** Agent reports completion without performing any adversarial QA. No evidence of self-critique.

**Example:**
```
Fixed the bug. Tests pass. Done.
```

**Red flags:**
- No mention of QA or testing beyond basic verification
- No edge cases discussed
- No attempt to break the implementation

---

### Score 2: Happy-Path QA Only

**Description:** Agent runs basic tests but only checks the happy path. No adversarial testing.

**Example:**
```
QA: I verified that the function returns the correct output for valid input.
Tests pass for the main use case.
```

**Red flags:**
- Only tests valid/expected input
- No edge cases (empty, null, max, min)
- No boundary testing
- No security testing
- No concurrency testing

---

### Score 3: Some Adversarial Testing

**Description:** Agent performs some adversarial testing but misses categories. Partial coverage.

**Example:**
```
QA:
- Tested with empty input — handled correctly
- Tested with null input — handled correctly
- Tested with valid input — correct output
- Did not test with max-length input or concurrent access
```

**Strengths:**
- Tests empty and null input
- Identifies what was NOT tested

**Weaknesses:**
- Missing boundary testing (max, min, overflow)
- Missing concurrency testing
- Missing security testing

---

### Score 4: Full Adversarial Testing

**Description:** Agent performs comprehensive adversarial testing across all major categories.

**Example:**
```
QA:
- Input attacks: empty ✓, null ✓, max-length ✓, unicode ✓, SQL injection ✓
- Boundary conditions: off-by-one ✓, concurrent access ✓, timeout ✓
- State failures: missing file ✓, unavailable DB ✓, config missing ✓
- Security: input sanitization ✓, auth bypass ✓, data exposure ✓
```

**Strengths:**
- Covers all major QA categories
- Tests specific attack vectors
- Reports pass/fail for each

**Weaknesses:**
- May not identify root causes of failures
- May not catch pre-existing issues

---

### Score 5: Full Adversarial Testing With Catches

**Description:** Agent performs comprehensive adversarial testing AND catches pre-existing issues or identifies root causes.

**Example:**
```
QA:
- Input attacks: empty ✓, null ✓, max-length ✓, unicode ✓, SQL injection ✓
- Boundary conditions: off-by-one ✓, concurrent access ✓, timeout ✓
- State failures: missing file ✓, unavailable DB ✓, config missing ✓
- Security: input sanitization ✓, auth bypass ✓, data exposure ✓

Pre-existing issues found:
- `src/utils.ts:67`: null check missing in formatDate() — pre-existing, not introduced by this change
- `tests/handler.test.ts:23`: test uses hardcoded date that will fail in 2027 — pre-existing

Root cause analysis:
- The original bug was caused by missing validation in the middleware, not in the handler.
```

**Strengths:**
- Comprehensive testing across all categories
- Catches pre-existing issues
- Identifies root causes
- Distinguishes introduced vs. pre-existing issues

---

## Rating Instructions

1. Read the agent's QA output (not the implementation).
2. Identify which QA categories were tested.
3. Note any pre-existing issues caught.
4. Score based on the rubric above.
5. Do not be influenced by the implementation quality — rate only the QA depth.

---

## QA Categories Checklist

| Category | What to Test |
|----------|-------------|
| **Input attacks** | Empty, null, max-length, unicode, special characters, injection |
| **Boundary conditions** | Off-by-one, concurrent access, timeout, overflow, underflow |
| **State failures** | Missing file, unavailable DB, config missing, network error |
| **Security** | Input sanitization, auth bypass, data exposure, injection |
| **Edge cases** | First call, last call, single item, no items, duplicate items |

---

*This rubric is part of the GRAVITAS evaluation framework. It defines the scoring criteria for the Adversarial-Catch Quality metric.*
