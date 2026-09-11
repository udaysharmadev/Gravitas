# Multi-File Refactor — Before vs After GRAVITAS

**Task:** Extract the repeated auth check from all route handlers into shared middleware.

---

## ❌ Without GRAVITAS (Normal Gemini)

```typescript
// Created auth middleware
export const authMiddleware = (req, res, next) => {
  if (!req.session?.userId) return res.status(401).json({ error: 'Unauthorized' });
  next();
};
```

> "I've created the middleware! You'll need to add it to your routes. I also cleaned up some other stuff while I was in there. Let me know!"

**Problems:**
- Created middleware but never updated the actual routes (task half-done)
- "Cleaned up other stuff" — unauthorized scope expansion
- No tests run. No VERDICT.

---

## ✅ With GRAVITAS

**Tier: 1** — 5 files, clear scope

**Recon** (parallel):
```
[read src/routes/posts.ts] + [read src/routes/users.ts] + [read src/routes/comments.ts]
+ [grep "session.*userId" src/routes/] + [find src/middleware/ -type f]
```

Found: identical auth check repeated at posts.ts:12, users.ts:8, comments.ts:15.
`src/middleware/` directory exists but is empty.

**Plan:**

| # | File | Change | Risk |
|---|------|--------|------|
| 1 | src/middleware/auth.ts | create middleware | if wrong, all auth breaks |
| 2 | src/middleware/auth.test.ts | 4 tests | none |
| 3 | src/routes/posts.ts:12 | inline → middleware | caught by test suite |
| 4 | src/routes/users.ts:8 | same | same |
| 5 | src/routes/comments.ts:15 | same | same |

Failure modes: if middleware runs after route handler → test catches it. If one route missed → 26 existing tests catch it.

**Evidence:**
```
$ tsc --noEmit
(clean)

$ eslint . --max-warnings 0
(clean)

$ vitest run --reporter=verbose
  ✓ middleware › requireAuth › calls next() (3ms)
  ✓ middleware › requireAuth › 401 no session (2ms)
  ✓ middleware › requireAuth › 401 no userId (2ms)
  ✓ middleware › requireAuth › does not modify request (2ms)
  ✓ posts › GET /posts (unauthorized) (8ms)
  ✓ posts › GET /posts (authorized) (11ms)
  [... all 26 existing tests ...]
  Tests: 30 passed, 30 total (was 26 — 4 new middleware tests)

VERDICT: PASS
```

## What Changed
- `src/middleware/auth.ts` — new shared `requireAuth` middleware
- `src/middleware/auth.test.ts` — 4 unit tests
- `src/routes/posts.ts`, `users.ts`, `comments.ts` — inline check replaced with middleware
- Zero scope expansion. Zero unasked-for cleanup.
