# Security Fix — Before vs After GRAVITAS

**Task:** Fix the SQL injection vulnerability in the user search endpoint.

---

## ❌ Without GRAVITAS (Normal Gemini)

```typescript
// Added input sanitization
const query = userInput.replace(/[^a-zA-Z0-9]/g, '');
const sql = `SELECT * FROM users WHERE name = '${query}'`;
```

> "I've added input sanitization to prevent SQL injection. This should be secure now!"

**Problems:**
- Sanitization regex is bypassable (still injectable with certain inputs)
- Missed a second injection point in the same file
- Zero security tests added
- "Should be secure" — unverified
- No VERDICT

---

## ✅ With GRAVITAS

**Tier: 2** — security change, high stakes

**Recon** (parallel):
```
[read src/users/search.ts] + [read src/users/search.test.ts]
+ [grep "query.*\${" src/] + [git log -5 -- src/users/]
```

Found:
- `src/users/search.ts:15` — `` `SELECT * FROM users WHERE name = '${query}'` ``
- `src/users/search.ts:28` — `` `SELECT * FROM posts WHERE author = '${author}'` `` ← **second injection!**
- 8 existing tests, zero injection tests
- Raw `pg` driver — no ORM safety net

**Plan (Tier 2 — includes adversarial critique):**

| # | File | Change | Risk |
|---|------|--------|------|
| 1 | search.ts:15 | parameterized query | none — safer |
| 2 | search.ts:28 | parameterized query | none — safer |
| 3 | search.test.ts | add 5 injection tests | none |

Adversarial critique: regex sanitization is insufficient — parameterized queries are the only correct fix.

**Implementation:**

```typescript
// src/users/search.ts:15
const result = await db.query(
  'SELECT * FROM users WHERE name = $1',
  [query]  // ← parameterized — injection impossible
);

// src/users/search.ts:28
const posts = await db.query(
  'SELECT * FROM posts WHERE author = $1',
  [author]
);
```

```typescript
// 5 new injection tests in search.test.ts
it("rejects DROP TABLE", async () => {
  expect(await searchUsers("'; DROP TABLE users; --")).toEqual([]);
});
it("rejects OR 1=1", async () => {
  expect(await searchUsers("' OR '1'='1")).toEqual([]);
});
it("handles legitimate apostrophe (O'Brien)", async () => {
  expect((await searchUsers("O'Brien")).length).toBeGreaterThan(0);
});
// + 2 more edge cases
```

**Evidence:**
```
$ vitest run --reporter=verbose
  ✓ search › basic query (8ms)
  ✓ search › SQL injection: DROP TABLE (4ms)   ← NEW
  ✓ search › SQL injection: OR 1=1 (3ms)        ← NEW
  ✓ search › SQL injection: UNION (4ms)         ← NEW
  ✓ search › legitimate apostrophe (12ms)       ← NEW
  Tests: 13 passed, 13 total (was 8 — 5 new security tests)

VERDICT: PASS
```

## What Changed
- `src/users/search.ts:15,28` — **both** injection points fixed with parameterized queries
- `src/users/search.test.ts` — 5 injection tests added
