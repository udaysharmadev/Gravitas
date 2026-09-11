# Bug Fix — Before vs After GRAVITAS

**Task:** Fix the session timeout bug. Users are being logged out after 5 seconds.

---

## ❌ Without GRAVITAS (Normal Gemini)

```typescript
// Increased the timeout value
const SESSION_TIMEOUT = 30000; // was 5000
```

> "I've updated the session timeout to 30 seconds. This should fix the logout issue. Let me know if you need anything else!"

**Problems:**
- Edited without reading the file first
- No plan, no risk analysis
- "Should fix" — unverified claim
- No tests run, no evidence cited
- Preamble + closing offer

---

## ✅ With GRAVITAS

**Recon** (parallel, one round-trip):
```
[read src/auth/session.ts] + [read src/auth/session.test.ts]
+ [grep SESSION_TIMEOUT src/] + [git log -5 -- src/auth/session.ts]
```

Found:
- `src/auth/session.ts:23` → `const SESSION_TIMEOUT = 5_000`
- `src/auth/session.test.ts:47` → `expect(timeout).toBe(5000)` ← **must update**
- Git: timeout reduced 30000→5000 six weeks ago (commit "perf: reduce session timeout")
- 2 middleware files import session.ts → need full suite, not just auth tests

**Plan:**

| # | File | Location | Change | Risk |
|---|------|----------|--------|------|
| 1 | src/auth/session.ts | line 23 | 5_000 → 30_000 | test asserts old value |
| 2 | src/auth/session.test.ts | line 47 | toBe(5000) → toBe(30_000) | none |

Failure modes: grepped for other `5000` assertions — none found.

**Implementation:**

```typescript
// src/auth/session.ts:23
const SESSION_TIMEOUT = 30_000; // 30s — was 5s (regressed 6w ago in perf commit)
```

```typescript
// src/auth/session.test.ts:47
expect(timeout).toBe(30_000);
```

**Evidence:**
```
$ tsc --noEmit
(no output — clean)

$ eslint . --max-warnings 0
(no output — clean)

$ vitest run --reporter=verbose
  ✓ auth › session timeout (12ms)
  ✓ auth › login flow (45ms)
  ✓ middleware › auth check (22ms)
  ✓ middleware › session validation (18ms)
  Tests: 47 passed, 47 total, 0 skipped

VERDICT: PASS
```

## What Changed
- `src/auth/session.ts:23` — SESSION_TIMEOUT 5_000 → 30_000
- `src/auth/session.test.ts:47` — assertion updated to match
