# Memory Templates

Drop-in `GRAVITAS_MEMORY.md` files for common tech stacks.
Copy to your project root and customize with real values.

---

## Next.js + Prisma

```markdown
# GRAVITAS Memory — Next.js + Prisma Project

## User
- Stack: Next.js 14 (App Router) + Prisma + PostgreSQL
- Test runner: Vitest (not Jest — don't use jest commands)
- Lint: ESLint with Next.js config
- Deploy: Vercel

## Project
- DB schema at: prisma/schema.prisma
- API routes in: src/app/api/
- Server components in: src/app/
- Client components in: src/components/
- Prisma client: import { db } from '@/lib/db'

## Conventions
- Use server components by default (no 'use client' unless needed)
- Mutations through Server Actions (not API routes where possible)
- Form validation with Zod
- Error boundaries around async components

## Session Failures
[none yet]
```

---

## FastAPI + SQLAlchemy

```markdown
# GRAVITAS Memory — FastAPI + SQLAlchemy Project

## User
- Stack: FastAPI + SQLAlchemy 2.0 + PostgreSQL + Alembic
- Test runner: pytest with pytest-asyncio
- Type checking: mypy strict mode
- Lint: ruff

## Project
- DB models at: app/models/
- API routers at: app/routers/
- Business logic at: app/services/
- DB session: from app.database import get_db (dependency injection)
- Migrations: alembic upgrade head

## Conventions
- All endpoints async (async def)
- Use Pydantic schemas for request/response (not raw dicts)
- Database sessions via FastAPI Depends(get_db)
- Background tasks for async ops (celery or FastAPI BackgroundTasks)

## Session Failures
[none yet]
```

---

## React Native + Expo

```markdown
# GRAVITAS Memory — React Native + Expo Project

## User
- Stack: React Native + Expo SDK 51 + TypeScript
- Test runner: Jest + React Native Testing Library
- State: Zustand (not Redux)
- Navigation: Expo Router (file-based)

## Project
- Screens at: app/(screens)/
- Components at: components/
- State stores at: stores/
- API calls via: lib/api.ts (axios instance)
- Assets at: assets/

## Conventions
- No StyleSheet.create — use Tailwind (NativeWind)
- Always test on both iOS and Android
- Use expo-constants for env vars (not process.env)
- Mock native modules in tests: __mocks__/

## Session Failures
[none yet]
```

---

## Rust + Axum

```markdown
# GRAVITAS Memory — Rust + Axum Project

## User
- Stack: Rust + Axum + SQLx + PostgreSQL
- Test runner: cargo test
- Lint: clippy -D warnings

## Project
- Routes at: src/routes/
- Handlers at: src/handlers/
- Models at: src/models/
- DB pool: use sqlx::PgPool (passed via State)
- Migrations: sqlx migrate run

## Conventions
- All errors via custom AppError type (impl IntoResponse)
- Use #[instrument] for tracing
- Integration tests in tests/ directory
- Unit tests inline (mod tests at bottom of each file)

## Session Failures
[none yet]
```

---

## Go + Chi Router

```markdown
# GRAVITAS Memory — Go + Chi Project

## User
- Stack: Go 1.22 + Chi router + pgx + PostgreSQL
- Test runner: go test ./...
- Lint: staticcheck

## Project
- Handlers at: internal/handlers/
- Models at: internal/models/
- DB queries at: internal/db/
- Entry point: cmd/server/main.go
- Config: internal/config/config.go (env vars via os.Getenv)

## Conventions
- Errors wrapped with fmt.Errorf("context: %w", err)
- Tests use testify assertions
- DB queries via pgx (not database/sql)
- Middleware in internal/middleware/

## Session Failures
[none yet]
```

---

## Django + DRF

```markdown
# GRAVITAS Memory — Django + DRF Project

## User
- Stack: Django 5 + Django REST Framework + PostgreSQL + Celery
- Test runner: pytest + pytest-django
- Lint: ruff + mypy

## Project
- Apps at: apps/ (each app is self-contained)
- Serializers at: apps/[name]/serializers.py
- Views at: apps/[name]/views.py (ViewSets)
- Celery tasks at: apps/[name]/tasks.py
- Settings: config/settings/ (base.py, dev.py, prod.py)

## Conventions
- Always use DRF serializers for validation (not forms)
- Auth via JWT (djangorestframework-simplejwt)
- Use select_related/prefetch_related to prevent N+1
- Tests use @pytest.mark.django_db

## Session Failures
[none yet]
```
