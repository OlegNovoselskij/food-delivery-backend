# Online Courses API

REST API of an online learning platform: course catalog, curriculum with video and materials, enrollments and
payments, progress tracking, quizzes with manual review, certificates, notifications over WebSocket, reviews,
analytics and an admin panel.

## Stack

FastAPI, SQLAlchemy 2, PostgreSQL 16, Alembic, Valkey (Redis-compatible), S3-compatible storage (RustFS in
development), SQLAdmin, ReportLab, Docker Compose. Tests: pytest, fakeredis. Lint and format: ruff.

## Quick start

```powershell
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed_demo
```

| URL | What |
|---|---|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/admin | Admin panel (admin account) |
| http://localhost:8025 | Mailpit: every email the system sends |
| http://localhost:9001 | Storage console (`rustfsadmin` / `rustfsadmin`) |

Demo accounts (all with password `Demo12345!`): `admin@demo.example.com`, teachers `olena@demo.example.com`,
`taras@demo.example.com`, `iryna@demo.example.com`, students `andrii@demo.example.com`, `maria@demo.example.com`
and others. To start over from an empty database: `docker compose down -v`.

## Commands

| Task | Command |
|---|---|
| Run the tests | `docker compose exec backend pytest` |
| Tests with coverage | `docker compose exec backend pytest --cov=app --cov-report=term-missing` |
| Lint and format | `docker compose exec backend ruff check . --fix` and `docker compose exec backend ruff format .` |
| New migration | `docker compose exec backend alembic revision --autogenerate -m "message"` |
| Apply migrations | `docker compose exec backend alembic upgrade head` |
| First admin | `docker compose exec backend python -m app.scripts.make_admin user@example.com` |
| Export the API schema | `docker compose exec backend python -m app.scripts.export_openapi openapi.json` |
| Restart the email worker after code changes | `docker compose restart worker` |

## Configuration (environment variables)

| Variable | Purpose | Default in Compose |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection | compose service `db` |
| `SECRET_KEY` | signs access tokens and one-time codes | development value, change in production |
| `ADMIN_SESSION_SECRET`, `ADMIN_COOKIE_SECURE` | admin panel session | development value, `false` |
| `ALLOWED_ORIGINS` | CORS and WebSocket origins | `localhost:5173`, `3000`, `8000` |
| `FRONTEND_URL` | base of the links inside emails | `http://localhost:5173` |
| `PUBLIC_API_URL` | public address of the API (QR code on certificates) | `http://localhost:8000` |
| `S3_*` | object storage (endpoint, public endpoint, keys, bucket) | RustFS |
| `VALKEY_URL` | cache, rate limits, realtime, nonces | compose service `valkey` |
| `EMAIL_PROVIDER` | `smtp` (Mailpit), `resend`, `brevo`, `console` | `smtp` |
| `GOOGLE_CLIENT_ID` | Google sign-in (set it in `.env`) | empty |
| `LOG_LEVEL`, `LOG_FORMAT` | logging (`text` or `json`) | `INFO`, `text` |
| `APP_ENV` | `development`, `production` (demo data refuses to run in production) | `development` |

## Architecture

Request path: **router → service → repository → database**. Routers only translate HTTP, services hold the business
rules and raise domain errors (mapped to HTTP statuses in one place: `app/api/error_handlers.py`), repositories
contain all SQL.

| Pattern | Where |
|---|---|
| Factory Method | `patterns/factories/enrollment_factory.py`, `grading_factory.py`, `recommendation_factory.py`, email sender factory |
| State | `patterns/states`: enrollment and quiz attempt life cycles |
| Strategy | `patterns/strategies`: grading by question type, course recommendations |
| Composite | `patterns/composite/course_tree.py`: course, module, lesson progress |
| Observer | `patterns/observer`: certificates, notifications, emails and cache invalidation react to domain events |
| Proxy | `patterns/proxy` (lesson access) and `patterns/proxy/catalog_cache.py` (caching) |
| Adapter | `patterns/adapters/payment_gateway.py`, `emails/senders.py`, `google_identity.py` |
| Template Method | `patterns/template/report.py` and the reports built on it |
| Singleton | shared instances through cached dependencies (`get_storage`, `get_redis`, `event_bus`) |

Notable decisions: emails go through a transactional outbox (written in the same transaction as the business change,
sent by `app/worker.py` with retries); files travel directly between the browser and the storage through presigned
URLs; one-time codes are stored as HMACs; the catalog cache is versioned and invalidated after the commit.

## Project layout

```
app/
  api/            routers (v1), health, error handlers
  admin/          SQLAdmin panel
  emails/         rendering, messages, provider adapters
  models/         SQLAlchemy models
  patterns/       design patterns
  reports/        analytics reports
  repository/     database access
  schemas/        Pydantic schemas
  scripts/        make_admin, seed_demo, export_openapi
  services/       business logic
  worker.py       email worker
tests/            unit and integration tests
alembic/          migrations
```
