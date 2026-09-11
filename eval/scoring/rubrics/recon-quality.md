# Rubric: Recon Quality

1-5 scale for rating the quality of the agent's reconnaissance before mutation. Designed for blinded human evaluation.

---

## Scoring Guide

### Score 1: No Recon

**Description:** Agent edits files without reading them first. First tool call is a mutation.

**Example:**
```
[Agent immediately edits src/middleware/session.ts without reading it first]
```

**Red flags:**
- First tool call is `edit` or `write`
- No file reads before mutation
- No understanding of current state

---

### Score 2: Minimal Recon

**Description:** Agent reads the target file only. No related files, config, or tests.

**Example:**
```
[Agent reads src/middleware/session.ts, then immediately edits it]
```

**Red flags:**
- Only reads the target file
- Does not read related files
- Does not read tests
- Does not check config

---

### Score 3: Basic Recon

**Description:** Agent reads target file and some related files. May miss tests or config.

**Example:**
```
[Agent reads:
- src/middleware/session.ts (target)
- src/routes/api.ts (related route file)
Then edits session.ts]
```

**Strengths:**
- Reads target file
- Reads at least one related file

**Weaknesses:**
- Does not read tests
- Does not check config
- Does not detect conventions

---

### Score 4: Standard Recon

**Description:** Agent reads target, related files, config, and tests. Detects conventions.

**Example:**
```
[Agent reads:
- src/middleware/session.ts (target)
- src/routes/api.ts (related routes)
- src/middleware/index.ts (middleware registration)
- tests/middleware.test.ts (existing tests)
- .prettierrc (style config)
- package.json (dependencies)
Then edits session.ts]
```

**Strengths:**
- Reads target + related + config + tests
- Detects style conventions
- Understands middleware registration pattern

**Weaknesses:**
- May not check git history
- May not check for concurrent modifications

---

### Score 5: Deep Recon

**Description:** Agent performs comprehensive recon: module tree, dependencies, git history, conventions, blockers.

**Example:**
```
[Agent reads:
- src/middleware/session.ts (target)
- src/routes/api.ts (related routes)
- src/middleware/index.ts (middleware registration)
- tests/middleware.test.ts (existing tests)
- .prettierrc (style config)
- package.json (dependencies)
- git log --oneline -10 -- src/middleware/session.ts (recent changes)
- git diff HEAD~3 -- src/middleware/session.ts (recent modifications)

Agent also:
- Checks for symlinks in middleware directory
- Verifies test runner is configured
- Identifies naming conventions from 3+ files
- Notes that session.ts was modified 2 days ago (concurrent modification risk)
]
```

**Strengths:**
- Comprehensive module tree exploration
- Git history for context
- Convention detection from multiple files
- Concurrent modification awareness
- Blocker identification

---

## Rating Instructions

1. Read the agent's tool call log (not the implementation).
2. Identify which files were read before the first mutation.
3. Note the depth and breadth of recon.
4. Score based on the rubric above.
5. Do not be influenced by the implementation quality — rate only the recon.

---

## Recon Depth Checklist

| Element | Required for Score 3+ | Required for Score 5 |
|---------|----------------------|---------------------|
| Target file | ✓ | ✓ |
| Related files (1+) | ✓ | ✓ |
| Config files | — | ✓ |
| Test files | — | ✓ |
| Convention detection | — | ✓ |
| Git history | — | ✓ |
| Concurrent modification check | — | ✓ |

---

*This rubric is part of the GRAVITAS evaluation framework. It defines the scoring criteria for the Recon Quality metric.*
