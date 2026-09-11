# Rubric: Plan Quality

1-5 scale for rating the quality of the agent's planning before execution. Designed for blinded human evaluation.

---

## Scoring Guide

### Score 1: No Plan

**Description:** Agent jumps directly to execution without any planning. No structured approach.

**Example:**
```
[Agent immediately starts editing files without any plan or discussion]
```

**Red flags:**
- First tool call is a mutation (edit/write)
- No discussion of approach
- No risk analysis
- No file identification

---

### Score 2: Vague Plan

**Description:** Agent produces a plan but it lacks specificity. No concrete files, steps, or risks.

**Example:**
```
Plan:
1. Find the issue
2. Fix it
3. Test it
4. Done
```

**Red flags:**
- Steps are generic (not task-specific)
- No file paths mentioned
- No risk analysis
- No evidence of reconnaissance

---

### Score 3: Structured Plan But Incomplete

**Description:** Agent produces a structured plan with specific steps but missing risk analysis or evidence.

**Example:**
```
Plan:
1. Read src/middleware/session.ts to understand current behavior
2. Add check for /api/internal routes
3. Run tests
4. Verify fix

Steps: 4
Files: src/middleware/session.ts, tests/middleware.test.ts
```

**Strengths:**
- Specific files listed
- Steps are concrete
- Includes verification step

**Weaknesses:**
- No risk analysis (what could go wrong?)
- No adversarial critique
- No reversibility assessment

---

### Score 4: Structured Plan With Risks

**Description:** Agent produces a structured plan with steps, files, and risk analysis. May lack adversarial critique.

**Example:**
```
Plan:
1. Read src/middleware/session.ts and tests/middleware.test.ts
   - Risk: Session middleware may have changed since last read
   - Evidence: File content matches expectations
2. Add route check at line 23
   - Risk: May break existing route matching
   - Evidence: Tests pass after change
3. Add test for /api/internal routes
   - Risk: Test may not cover all edge cases
   - Evidence: Test passes for main case
4. Run full test suite
   - Risk: Pre-existing failures may mask issues
   - Evidence: All tests pass

Tier: 1 (reversible, local scope)
```

**Strengths:**
- Specific files and line numbers
- Risk analysis per step
- Evidence criteria per step
- Tier classification

**Weaknesses:**
- No adversarial critique
- No plan revision based on critique

---

### Score 5: Full Plan With Critique and Revision

**Description:** Agent produces a comprehensive plan with steps, risks, evidence, adversarial critique, and revision.

**Example:**
```
Plan:
1. Read src/middleware/session.ts and tests/middleware.test.ts
   - Risk: Session middleware may have changed since last read
   - Evidence: File content matches expectations
2. Add route check at line 23
   - Risk: May break existing route matching
   - Evidence: Tests pass after change
3. Add test for /api/internal routes
   - Risk: Test may not cover all edge cases
   - Evidence: Test passes for main case
4. Run full test suite
   - Risk: Pre-existing failures may mask issues
   - Evidence: All tests pass

Tier: 1 (reversible, local scope)

Adversarial Critique:
- Weakest assumption: The route pattern matching is correct. If routes
  use a different matching strategy, the fix may not work.
- Most likely to break: Existing tests that rely on /api/internal routes
  being unauthenticated.
- Edge case not covered: What if the route has query parameters?
  The fix should handle /api/internal/* with any query string.

Revised Plan:
- Step 2: Verify route matching strategy before adding check
- Step 3: Add test for /api/internal routes with query parameters
- Step 4: Specifically check that existing internal route tests still pass
```

**Strengths:**
- Comprehensive plan with all elements
- Adversarial critique with structured questions
- Plan revision based on critique
- Specific, actionable steps

---

## Rating Instructions

1. Read the agent's plan output (not the implementation).
2. Identify which plan elements are present.
3. Note the adversarial critique quality.
4. Score based on the rubric above.
5. Do not be influenced by the implementation quality — rate only the plan.

---

## Plan Elements Checklist

| Element | Required for Score 3+ | Required for Score 5 |
|---------|----------------------|---------------------|
| Specific files | ✓ | ✓ |
| Numbered steps | ✓ | ✓ |
| Risk analysis | — | ✓ |
| Evidence criteria | — | ✓ |
| Tier classification | — | ✓ |
| Adversarial critique | — | ✓ |
| Plan revision | — | ✓ |

---

*This rubric is part of the GRAVITAS evaluation framework. It defines the scoring criteria for the Plan Quality metric.*
