# Rubric: Outcome-First-ness

1-5 scale for rating the quality of agent response structure. Designed for blinded human evaluation.

---

## Scoring Guide

### Score 1: Process Narrative

**Description:** Response leads with tool-by-tool travelogue. No structured outcome. User must read through narrative to find results.

**Example:**
```
I started by reading the session handler file. I noticed it was checking
the route path but not for /api/internal routes. So I added a check for
that. Then I ran the tests and they passed. I also noticed the test file
could use more coverage so I added a test for the internal route case.
Then I ran the tests again and everything passes.
```

**Red flags:**
- Starts with "I started by..." or "First, I..."
- Lists tools used before stating outcome
- Numbered steps of process
- No file:line references
- No command output cited

---

### Score 2: Partial Outcome-First

**Description:** Response mentions the outcome but buries key information. Structure is present but incomplete.

**Example:**
```
Fixed the authentication bypass. The session middleware was skipping
checks for /api/internal routes. I added the check and now all routes
require authentication. Tests pass. I also added a test for the new behavior.
```

**Red flags:**
- Outcome mentioned but not structured (no template)
- No file:line references
- No command output cited
- Key details buried in sentences

**What would make it a 3:**
- Add file:line references
- Add structured template (What changed / Verified / Needs input)

---

### Score 3: Outcome-First But Lacks Specificity

**Description:** Response leads with outcome using a template, but lacks specific file:line references or evidence citations.

**Example:**
```
## Bug Fix: Authentication bypass — DONE

**What changed:**
- Session middleware now checks /api/internal routes

**Verified:**
- Tests pass

**Needs your input:**
- None
```

**Red flags:**
- "Session middleware" without file:line
- "Tests pass" without command and count
- No specific behavioral description

**What would make it a 4:**
- Add file:line references: `src/middleware/session.ts:23`
- Add command output: `npm test — 14/14 passing`

---

### Score 4: Outcome-First With Specifics and Evidence

**Description:** Response leads with specific outcome, includes file:line references, and cites verification evidence.

**Example:**
```
## Bug Fix: Authentication bypass — DONE

**What changed:**
- `src/middleware/session.ts:23` — added check for /api/internal routes
  in the session validation middleware

**Verified:**
- `npm test` — 14/14 passing (including new test at
  `tests/middleware.test.ts:45`)
- `npx tsc --noEmit` — no type errors

**Needs your input:**
- None
```

**Strengths:**
- Structured template
- File:line references
- Command output cited
- New test referenced

**What would make it a 5:**
- State uncertainty if any
- Use clear, concise writing (one idea per sentence, active verbs)

---

### Score 5: Outcome-First With Specifics, Evidence, and Clarity

**Description:** Response leads with specific outcome, cites evidence, states uncertainty, and uses clear, concise writing.

**Example:**
```
## Bug Fix: Authentication bypass — DONE

**What changed:**
- `src/middleware/session.ts:23` — added session validation check for
  /api/internal routes. Previously these routes were excluded from
  authentication.

**Verified:**
- `npm test` — 14/14 passing (including new test at
  `tests/middleware.test.ts:45`)
- `npx tsc --noEmit` — no type errors

**Needs your input:**
- None
```

**Strengths:**
- Structured template
- File:line references with context
- Command output cited with counts
- Clear, concise writing
- One idea per sentence
- Active verbs
- No filler

---

## Rating Instructions

1. Read the agent's response (not the implementation).
2. Identify the first thing the user would read.
3. Score based on the rubric above.
4. Note specific strengths and weaknesses.
5. Do not be influenced by the implementation quality — rate only the response structure.

---

## Inter-Rater Reliability

- 3 independent raters per response.
- Calculate Cohen's kappa for ordinal agreement.
- If kappa < 0.6, convene a calibration session.
- If kappa < 0.4 after calibration, exclude the metric.

---

*This rubric is part of the GRAVITAS evaluation framework. It defines the scoring criteria for the Outcome-First-ness metric.*
