---
name: gravitas-security
description: >
  Deep security review mode for GRAVITAS. Adds threat modeling, OWASP Top 10
  checks, injection prevention patterns, auth/session security, and
  security-specific test requirements. Load for any auth, input handling,
  database, or API work.
triggers:
  - "security"
  - "auth"
  - "authentication"
  - "authorization"
  - "injection"
  - "sql"
  - "xss"
  - "csrf"
  - "vulnerability"
  - "password"
  - "token"
  - "session"
  - "permission"
  - "rbac"
  - "api key"
  - "secret"
---

# GRAVITAS — Security Extension

Deep security review mode. Load in addition to `skills/gravitas/SKILL.md`.
All security tasks are **Tier 2** minimum. No exceptions.

---

## Security Recon Additions

Beyond standard recon, always check:

```bash
# SQL injection patterns
grep -rn "query.*\$\{" src/ --include="*.ts"
grep -rn "execute.*+.*req\." src/ --include="*.ts"
grep -rn "\.raw\|\.execute\|\.query" src/ --include="*.ts" | grep -v parameterized

# XSS patterns
grep -rn "innerHTML\|outerHTML\|document\.write\|insertAdjacentHTML" src/ --include="*.ts"
grep -rn "dangerouslySetInnerHTML" src/ --include="*.tsx"

# Hardcoded secrets
grep -rn "password\s*=\s*['\"]" src/ --include="*.ts"
grep -rn "api.key\s*=\s*['\"]" src/ --include="*.ts"
grep -rn "secret\s*=\s*['\"]" src/ --include="*.ts"
grep -rn "token\s*=\s*['\"]" src/ --include="*.ts"

# Auth bypass
grep -rn "skipAuth\|bypassAuth\|noAuth\|isAdmin.*=.*true" src/ --include="*.ts"

# Mass assignment
grep -rn "Object\.assign.*req\.body\|spread.*req\.body\|\.create(req\.body)" src/

# Insecure direct object reference
grep -rn "req\.params\.id\|req\.query\.id" src/ -A 3 | grep -v "userId.*session"

# Path traversal
grep -rn "readFile.*req\.\|__dirname.*req\." src/
```

---

## OWASP Top 10 Checklist

For every security change, verify:

```
□ A01 Broken Access Control    — auth checked before data access
□ A02 Cryptographic Failures   — no plaintext passwords/secrets
□ A03 Injection                — parameterized queries everywhere
□ A04 Insecure Design          — threat model considered
□ A05 Security Misconfiguration— no debug mode in prod, no default creds
□ A06 Vulnerable Components    — no known-vulnerable dependencies
□ A07 Auth/Session Failures    — session invalidated on logout
□ A08 Software/Data Integrity  — dependencies verified, no eval()
□ A09 Security Logging         — auth failures logged, no PII in logs
□ A10 SSRF                     — no unvalidated URL fetching
```

---

## Security Anti-Patterns

### Injection (A03)

```typescript
BAD:  db.query(`SELECT * FROM users WHERE id = ${req.params.id}`)
BAD:  db.query("SELECT * FROM users WHERE id = " + id)
GOOD: db.query('SELECT * FROM users WHERE id = $1', [id])
```

### Broken Auth (A07)

```typescript
BAD:  if (req.headers['x-admin'] === 'true') { grantAdmin(); }
BAD:  const user = { ...req.body, isAdmin: false }; // mass assignment — override possible
GOOD: const user = { username: req.body.username, email: req.body.email }; // explicit allowlist
```

### Hardcoded Secrets (A02)

```typescript
BAD:  const JWT_SECRET = 'mysecretkey123';
GOOD: const JWT_SECRET = process.env.JWT_SECRET;
      if (!JWT_SECRET) throw new Error('JWT_SECRET not set');
```

### Missing Auth Check (A01)

```typescript
BAD:  router.delete('/users/:id', async (req, res) => {
        await deleteUser(req.params.id); // no auth check!
      });
GOOD: router.delete('/users/:id', requireAuth, requireAdmin, async (req, res) => {
        await deleteUser(req.params.id);
      });
```

---

## Required Security Tests

Every security fix must include tests that **demonstrate the vulnerability is fixed**:

```typescript
describe('SQL injection prevention', () => {
  const payloads = [
    "'; DROP TABLE users; --",
    "' OR '1'='1",
    "' UNION SELECT password FROM admins --",
    "1; UPDATE users SET password = 'hacked'",
    "' OR 1=1 --",
  ];

  payloads.forEach(payload => {
    it(`blocks: ${payload.slice(0, 30)}...`, async () => {
      const result = await searchUsers(payload);
      expect(result).toEqual([]); // no data leaked, no crash
    });
  });
});

describe('Auth protection', () => {
  it('returns 401 on missing auth token', async () => {
    const res = await request(app).delete('/users/1');
    expect(res.status).toBe(401);
  });
  it('returns 403 on insufficient permissions', async () => {
    const res = await request(app)
      .delete('/users/1')
      .set('Authorization', `Bearer ${regularUserToken}`);
    expect(res.status).toBe(403);
  });
});
```

---

## Security Verification Chain

```bash
# Standard chain
tsc --noEmit && eslint . --max-warnings 0 && vitest run

# Security-specific grep checks
grep -rn "query.*\${" src/ --include="*.ts" | wc -l    # should be 0
grep -rn "innerHTML" src/ --include="*.ts" | wc -l     # should be 0
grep -rn "password.*['\"]" src/ --include="*.ts"       # should be 0

# Dependency audit
npm audit --audit-level=high                            # 0 high/critical

# Report
echo "Injection patterns: $(grep -rn "query.*\${"  src/ | wc -l) (want: 0)"
echo "XSS patterns:       $(grep -rn "innerHTML"    src/ | wc -l) (want: 0)"
echo "npm audit high:     $(npm audit --audit-level=high 2>&1 | grep 'found 0')"
```

---

## VERDICT for Security Tasks

Security VERDICT requires ALL of:
- Standard: tests pass, lint clean, types clean
- **Security**: 0 injection patterns found
- **Security**: security tests present and passing
- **Security**: no new hardcoded secrets
- **Security**: npm audit 0 high/critical

```
VERDICT: PASS (Security)

Tests:     47/47 (5 new security tests)
Lint:      clean
Types:     clean
Injection: 0 patterns found
Secrets:   0 hardcoded found
Audit:     0 high/critical vulnerabilities
```
