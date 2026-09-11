# Protocol Extensions

Optional extensions that add specialized capabilities beyond the core 10 pillars. These are loaded on-demand for specific task types.

---

## 1. Security Extension

### 1.1 Purpose

Adds security-specific behaviors for tasks involving authentication, authorization, cryptography, or sensitive data.

### 1.2 Loaded When

- Task involves auth, tokens, passwords, keys, or secrets
- Task involves user input handling
- Task involves data encryption or decryption
- Task involves access control

### 1.3 Additional Behaviors

| Behavior | Description |
|----------|-------------|
| Threat modeling | Identify attack surfaces before implementation |
| Input validation | Validate all user inputs at system boundaries |
| Secret scanning | Scan for accidentally committed secrets |
| Dependency audit | Check dependencies for known vulnerabilities |
| Security review | Adversarial security review before completion |

### 1.4 Verification Commands

```bash
# Secret scanning
grep -r "password\|secret\|key\|token" --include="*.{ts,js,py,go,rs}" .

# Dependency audit
npm audit
cargo audit
pip audit

# Linting for security patterns
eslint --plugin security .
```

---

## 2. Performance Extension

### 2.1 Purpose

Adds performance-specific behaviors for tasks involving optimization, profiling, or scalability.

### 2.2 Loaded When

- Task involves performance improvement
- Task involves profiling or benchmarking
- Task involves database queries or API calls
- Task involves caching or memoization

### 2.3 Additional Behaviors

| Behavior | Description |
|----------|-------------|
| Baseline measurement | Measure performance before changes |
| Profiling | Profile hot paths before optimizing |
| Benchmarking | Run benchmarks before and after changes |
| Regression detection | Detect performance regressions |
| Documentation | Document performance characteristics |

### 2.4 Verification Commands

```bash
# Benchmarking
npm run benchmark
cargo bench
pytest --benchmark

# Profiling
node --prof app.js
python -m cProfile script.py

# Load testing
ab -n 1000 -c 10 http://localhost:3000/
```

---

## 3. Accessibility Extension

### 3.1 Purpose

Adds accessibility-specific behaviors for tasks involving UI, UX, or user-facing content.

### 3.2 Loaded When

- Task involves UI components
- Task involves user-facing content
- Task involves forms or input fields
- Task involves navigation or routing

### 3.3 Additional Behaviors

| Behavior | Description |
|----------|-------------|
| WCAG compliance | Check against WCAG 2.1 AA standards |
| Screen reader testing | Verify screen reader compatibility |
| Keyboard navigation | Verify keyboard-only navigation |
| Color contrast | Check color contrast ratios |
| ARIA attributes | Verify proper ARIA attribute usage |

### 3.4 Verification Commands

```bash
# Accessibility linting
eslint --plugin jsx-a11y .
axe-core --rules WCAG2AA

# Screen reader testing
# Manual testing with VoiceOver (macOS) or NVDA (Windows)

# Keyboard navigation testing
# Manual testing with Tab, Shift+Tab, Enter, Escape
```

---

## 4. Data Extension

### 4.1 Purpose

Adds data-specific behaviors for tasks involving databases, migrations, or data processing.

### 4.2 Loaded When

- Task involves database schema changes
- Task involves data migration
- Task involves data validation
- Task involves data transformation

### 4.3 Additional Behaviors

| Behavior | Description |
|----------|-------------|
| Schema validation | Validate schema changes against existing data |
| Migration testing | Test migrations on sample data |
| Rollback planning | Plan rollback procedures for migrations |
| Data integrity | Verify data integrity after changes |
| Performance impact | Assess query performance impact |

### 4.4 Verification Commands

```bash
# Schema validation
prisma validate
drizzle-kit check

# Migration testing
prisma migrate dev --preview-feature
drizzle-kit generate

# Data integrity
SELECT COUNT(*) FROM table WHERE condition;
```

---

## 5. API Extension

### 5.1 Purpose

Adds API-specific behaviors for tasks involving REST, GraphQL, or other API protocols.

### 5.2 Loaded When

- Task involves API endpoints
- Task involves request/response handling
- Task involves authentication/authorization
- Task involves rate limiting or throttling

### 5.3 Additional Behaviors

| Behavior | Description |
|----------|-------------|
| Contract testing | Test against API contract/schema |
| Error handling | Verify proper error responses |
| Rate limiting | Verify rate limiting behavior |
| Authentication | Verify auth flows |
| Documentation | Update API documentation |

### 5.4 Verification Commands

```bash
# Contract testing
jest --testPathPattern=api
pytest tests/api/

# API documentation
swagger-cli validate openapi.yaml
graphql-codegen

# Load testing
artillery run load-test.yml
```

---

## 6. Extension Loading

### 6.1 Loading Rules

```python
def load_extensions(task_type: str, task_context: dict) -> list:
    """Load extensions based on task characteristics."""
    extensions = []
    
    if task_type in ["security", "auth", "crypto"] or task_context.get("involves_secrets"):
        extensions.append("security")
    
    if task_type in ["performance", "optimization", "profiling"] or task_context.get("performance_critical"):
        extensions.append("performance")
    
    if task_type in ["ui", "frontend", "accessibility"] or task_context.get("user_facing"):
        extensions.append("accessibility")
    
    if task_type in ["database", "migration", "data"] or task_context.get("involves_data"):
        extensions.append("data")
    
    if task_type in ["api", "endpoint", "rest", "graphql"] or task_context.get("involves_api"):
        extensions.append("api")
    
    return extensions
```

### 6.2 Token Impact

| Extension | Additional Tokens | When Loaded |
|-----------|------------------|-------------|
| Security | ~2,000 | Security tasks |
| Performance | ~1,500 | Performance tasks |
| Accessibility | ~1,500 | UI tasks |
| Data | ~1,500 | Database tasks |
| API | ~1,500 | API tasks |

### 6.3 Priority

Extensions are loaded after core pillars. If token budget is tight, core pillars take priority.

---

## 7. Custom Extensions

### 7.1 Creating Custom Extensions

Users can create custom extensions by following this template:

```markdown
# [Extension Name] Extension

## Purpose
[What this extension adds]

## Loaded When
[Trigger conditions]

## Additional Behaviors
| Behavior | Description |
|----------|-------------|
| [Behavior 1] | [Description] |
| [Behavior 2] | [Description] |

## Verification Commands
[Commands to verify behavior]

## Token Impact
[Approximate tokens]
```

### 7.2 Loading Custom Extensions

Place custom extensions in:
```
~/.agents/skills/gravitas/extensions/custom-[name].md
```

They will be loaded alongside core extensions when triggered.

---

*This document is part of the GRAVITAS advanced research phase. It defines optional protocol extensions for specialized task types.*
