---
name: gravitas-perf
description: >
  Performance analysis mode for GRAVITAS. Adds profiling patterns, benchmark
  requirements, algorithmic complexity analysis, and before/after measurement
  protocol. Load for any performance optimization work.
triggers:
  - "performance"
  - "perf"
  - "slow"
  - "optimize"
  - "optimization"
  - "benchmark"
  - "profiling"
  - "memory"
  - "cpu"
  - "latency"
  - "throughput"
  - "bottleneck"
  - "N+1"
  - "cache"
---

# GRAVITAS — Performance Extension

Performance analysis mode. Load in addition to `skills/gravitas/SKILL.md`.
All perf claims require **measured before/after numbers**. No guessing.

---

## Core Rule: Measure Before Optimizing

Never optimize without a baseline measurement. "This is slow" is not a baseline.

```
Baseline required:
  - What is the current latency/throughput? (measured, not estimated)
  - What is the target? (user's goal or SLA)
  - What is the profiler saying is hot? (not intuition)
```

---

## Performance Recon Additions

```bash
# Database — N+1 queries
grep -rn "\.find\|\.findOne\|\.select" src/ --include="*.ts" | grep -v "include\|join"

# Missing indexes
grep -rn "WHERE.*email\|WHERE.*username\|WHERE.*userId" src/ --include="*.ts"
# → check if these columns have DB indexes

# Unoptimized loops
grep -rn "for.*await\|forEach.*await" src/ --include="*.ts"
# → sequential async where parallel would work

# Missing memoization
grep -rn "\.map\|\.filter\|\.reduce" src/ --include="*.ts" -A 2 | grep "expensive\|compute\|calculate"

# Bundle size (frontend)
npx bundlesize 2>/dev/null || du -sh dist/ 2>/dev/null

# Memory leaks
grep -rn "setInterval\|addEventListener" src/ --include="*.ts" | grep -v "clearInterval\|removeEventListener"
```

---

## Measurement Protocol

### Before any optimization

```bash
# API latency (using autocannon, wrk, or k6)
autocannon -c 10 -d 10 http://localhost:3000/api/users
# Record: req/sec, latency p50/p95/p99

# Function benchmark (using vitest bench)
import { bench, describe } from 'vitest';
describe('processUsers', () => {
  bench('current', () => processUsers(testData));
});

# Memory
node --inspect src/server.js &
# heap snapshot before and after load
```

### Report format (required)

```
## Performance Baseline
- Endpoint: GET /api/users
- Before: 127ms p50, 842ms p99, 78 req/sec
- After:  23ms p50, 95ms p99, 512 req/sec
- Improvement: 5.5x p50, 8.9x p99, 6.6x throughput
```

---

## Common Performance Anti-Patterns

### N+1 Query Problem

```typescript
BAD:
const users = await db.query('SELECT * FROM users');
for (const user of users) {
  user.posts = await db.query('SELECT * FROM posts WHERE userId = $1', [user.id]);
  // N queries for N users → N+1 total
}

GOOD:
const users = await db.query(`
  SELECT u.*, json_agg(p.*) as posts
  FROM users u
  LEFT JOIN posts p ON p.userId = u.id
  GROUP BY u.id
`);
// 1 query total
```

### Sequential Async Where Parallel Works

```typescript
BAD:
const user = await fetchUser(id);
const posts = await fetchPosts(id);  // waits for user unnecessarily
const comments = await fetchComments(id);  // waits for posts

GOOD:
const [user, posts, comments] = await Promise.all([
  fetchUser(id),
  fetchPosts(id),
  fetchComments(id),  // all start simultaneously
]);
```

### Missing Cache for Expensive Computation

```typescript
BAD: function getPermissions(userId: string) {
  return db.query('SELECT * FROM permissions WHERE userId = $1', [userId]);
  // called on every request
}

GOOD: const cache = new Map<string, Permission[]>();
function getPermissions(userId: string) {
  if (cache.has(userId)) return cache.get(userId)!;
  const perms = await db.query(...);
  cache.set(userId, perms);
  setTimeout(() => cache.delete(userId), 60_000); // 1min TTL
  return perms;
}
```

### Missing Database Indexes

```sql
-- Check slow queries
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'user@example.com';
-- If: Seq Scan → MISSING INDEX

-- Fix
CREATE INDEX idx_users_email ON users(email);
-- After: Index Scan → fast
```

---

## Algorithmic Complexity Analysis

For any new algorithm, document complexity:

```typescript
/**
 * Finds duplicate usernames in O(n) time.
 * @complexity O(n) time, O(n) space
 *
 * BAD alternative: O(n²) nested loops
 */
function findDuplicates(usernames: string[]): string[] {
  const seen = new Set<string>();
  return usernames.filter(name => {
    if (seen.has(name)) return true;
    seen.add(name);
    return false;
  });
}
```

---

## Performance Verification

```bash
# Benchmark comparison
vitest bench --reporter=verbose

# Before/after latency comparison
autocannon -c 10 -d 30 http://localhost:3000/api/endpoint

# Bundle size change
du -sh dist/  # before and after

# Memory usage
node --max-old-space-size=512 -e "require('./dist/server')" &
sleep 5 && curl http://localhost:3000/api/heavy-endpoint
```

### VERDICT for Performance Tasks

```
VERDICT: PASS (Performance)

Baseline:    p50=127ms, p99=842ms, 78 req/sec
After:       p50=23ms,  p99=95ms,  512 req/sec
Improvement: 5.5x p50, 8.9x p99, 6.6x throughput
Tests:       47/47 (behavior unchanged)
Memory:      no increase in heap usage
```

**Never claim performance improvement without measured before/after numbers.**
