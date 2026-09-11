# Feature: Caching Layer

## Task
Add caching to API responses.

---

## BAD Output (Normal Agent)

```typescript
const cache = new Map();

export function getCached(key: string) {
  return cache.get(key);
}
```

**Problems:**
- No TTL — cache never expires
- No size limit — memory leak
- No tests
- No error handling

---

## GOOD Output (GRAVITAS)

### Recon (Explore Agent)

```
Read: src/api/routes.ts (15 endpoints)
Read: src/api/middleware.ts (existing middleware)
Read: package.json (no cache library)
Found: 8 GET endpoints could benefit from caching
```

### Plan (Plan Agent)

```
## Plan
1. src/cache.ts — create CacheManager
   Risk: memory leak without size limit
   Mitigation: LRU with max 1000 entries

2. src/cache.ts — add TTL support
   Risk: stale data if TTL too long
   Mitigation: default 5min, configurable

3. src/api/middleware.ts — add cache middleware
   Risk: cache stampede
   Mitigation: async locking

4. src/cache.test.ts — tests
   Risk: test isolation
   Mitigation: beforeEach cleanup
```

### Implementation (General Agent)

```typescript
// src/cache.ts
interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

export class CacheManager<T = unknown> {
  private cache = new Map<string, CacheEntry<T>>();
  private accessOrder: string[] = [];
  private maxSize: number;
  private defaultTTL: number;

  constructor(config: { maxSize?: number; defaultTTL?: number } = {}) {
    this.maxSize = config.maxSize ?? 1000;
    this.defaultTTL = config.defaultTTL ?? 5 * 60 * 1000;
  }

  get(key: string): T | undefined {
    const entry = this.cache.get(key);
    if (!entry) return undefined;
    if (Date.now() > entry.expiresAt) {
      this.delete(key);
      return undefined;
    }
    this.accessOrder = this.accessOrder.filter(k => k !== key);
    this.accessOrder.push(key);
    return entry.value;
  }

  set(key: string, value: T, ttl?: number): void {
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const lru = this.accessOrder.shift();
      if (lru) this.delete(lru);
    }
    this.cache.set(key, {
      value,
      expiresAt: Date.now() + (ttl ?? this.defaultTTL),
    });
    this.accessOrder = this.accessOrder.filter(k => k !== key);
    this.accessOrder.push(key);
  }

  delete(key: string): void {
    this.cache.delete(key);
    this.accessOrder = this.accessOrder.filter(k => k !== key);
  }
}
```

### Verification (Verify Agent)

```
=== TypeScript Verification ===
✓ Type-check passed
✓ Lint clean
✓ Tests passed: 52/52 (5 new)

VERDICT: PASS
```

### Final Report

```
## What Changed
- src/cache.ts — new CacheManager (LRU + TTL)
- src/cache.test.ts — 5 new tests
- src/api/middleware.ts — cache middleware
- src/api/routes.ts — applied to 8 GET endpoints

## Evidence
- 52/52 tests pass
- Lint clean

## Why
API responses were regenerating every request.
Caching reduces DB load ~80% for read-heavy endpoints.
LRU prevents memory leaks. TTL prevents stale data.
```
