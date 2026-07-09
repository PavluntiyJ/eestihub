# T08 — Housing from Postgres (SQLAlchemy + seed)

**Read first:** `docs/CONTEXT.md` (§2, §3, §5 — the
`GET /api/v1/housing/rents` contract, §7).
**Dependencies:** T05 accepted. **Role:** Backend (Python).
**Branch:** work in `master` (T09 — frontend tests — runs in parallel on
`feat/t09-e2e`; backend files do not overlap).

## Goal

The Postgres declared in the stack starts doing real work: rent data
moves from hardcode into the DB. A SQLAlchemy model, an idempotent seed
from the current mocks, the service reads from the DB. **The v1 API
contract does not change** — the frontend notices nothing, except one
refinement: `updated_at` becomes a real date (serialized to the same
`YYYY-MM-DD` string).

Postgres runs via `docker compose up -d db` (podman environment, the
`docker` alias works; connection parameters are in `.env.example`).

## Steps

1. Dependencies in `requirements.txt`: `sqlalchemy` 2.x and
   `psycopg[binary]` (pin versions per the file's convention).
2. `app/core/config.py`: a `database_url` setting (from the
   `DATABASE_URL` env var, defaulting to the local compose Postgres).
   Update `.env.example`.
3. `app/core/db.py`: engine + session factory (synchronous — enough for
   the MVP), a `get_session` FastAPI dependency.
4. `app/models/housing.py`: `DistrictRent` model (`district_rents`
   table): `id` PK, unique `name`, four int price fields, `lat`/`lon`
   float, `updated_at` date. `Base` lives in `app/models/`.
5. Seed `backend/scripts/seed_housing.py`: creates tables
   (`Base.metadata.create_all` — no Alembic in the MVP, orchestrator's
   decision) and **idempotently** (upsert by `name`) loads data from
   `app/services/housing_data.py` — the mock module remains the seed
   source. Run as `python -m scripts.seed_housing` from `backend/`.
6. `app/services/housing_service.py`: reads districts from the DB
   (ordered by `name`), response `updated_at` = max across rows. Change
   `HousingRentsResponse.updated_at` to `datetime.date`.
7. Route: with the DB unavailable — HTTP 503 (`Service Unavailable`),
   no stack trace in the response. The frontend already renders an
   unavailable state on any non-2xx/network error — leave it alone.
8. Tests: without a live Postgres (SQLite in-memory via a `get_session`
   override; mind type differences — the model must stay compatible):
   response shape, 8 districts after seeding the test session, 503 when
   the DB is down. Plus a manual live check: compose Postgres, seed,
   `curl` — the result is identical to the previous mock response
   (except the date type).
9. Commit: `feat(backend): serve housing rents from postgres`.

## Non-goals

- Do not change the §5 contract, v1 routes, tax code, or the frontend
  (at all).
- No Alembic, async engine, connection pools, or ORM models for taxes.
- Do not delete `housing_data.py` — it is now the seed source.

## Acceptance criteria

- [ ] `pytest` green without a running Postgres.
- [ ] Live run: `docker compose up -d db` → seed → `curl
      /api/v1/housing/rents` → 200, 8 districts, values match the old
      mocks, `updated_at: "2026-07-01"`.
- [ ] Re-running the seed does not duplicate rows (idempotency).
- [ ] DB stopped → the endpoint answers 503 (not a 500 with a stack
      trace); `/api/v1/health` and the calculator keep working without
      the DB as before.
- [ ] No changes under `frontend/`.

## On completion

Set T08 to `[R]` in `TODO.md` + a journal entry (what was verified and how).
