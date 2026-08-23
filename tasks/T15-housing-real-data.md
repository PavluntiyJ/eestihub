# T15 — Real housing data: snapshot history, ingest script, trends API

**Read first:** `docs/CONTEXT.md` (§2–§5, §7).
**Dependencies:** none. **Role:** Backend.
**Branch:** work in `main`.

## Context

Housing rents are served from the static seeded `district_rents` table
(8 rows, `updated_at: 2026-07-01`) — the biggest usefulness gap. This
task introduces time-stamped rent snapshots so the dashboard serves real,
dated data and can show history later. Source policy: **published
aggregate statistics only** (City24/KV.ee public market reports,
Statistics Estonia) — no scraping of listing pages, no logins, no captcha
circumvention. The orchestrator must approve the two API-contract
additions below at review and mirror them into CONTEXT §5.

## Steps

1. **Research + data file.** Find a citable public aggregate source for
   Tallinn average asking rents by district. Record source, retrieval
   date and license/ToS note in a short `backend/scripts/data/SOURCES.md`.
   Create `backend/scripts/data/rent_snapshots.csv`
   (`city,district_name,captured_on,avg_rent_1room,avg_rent_2room,avg_rent_3room,avg_utilities,source`).
   Fresh, source-backed values are mandatory. If no legally usable source
   provides the required district/room granularity, stop and record the
   blocker in `TODO.md` rather than presenting mock data as real.
2. **Model.** SQLAlchemy model `RentSnapshot` (table `rent_snapshots`):
   id PK, `city` (default `"Tallinn"`), `district_name`,
   `avg_rent_1room|2room|3room` int, `avg_utilities` int nullable,
   `captured_on` date, `source` varchar. Unique constraint on
   (`city`, `district_name`, `captured_on`) — idempotency key. Follow the
   existing `create_all` bootstrap pattern (no Alembic — standing
   orchestrator decision).
3. **Ingest script.** `python -m scripts.ingest_rents` parses the CSV and
   upserts snapshots (conflict-safe by the unique key, mirroring the seed
   style). Re-running is a no-op. The legacy seed stays untouched and is
   still required for bootstrap/tests.
4. **Service change.** `housing_service` prefers, per district, the most
   recent snapshot; falls back to `district_rents` when no snapshots
   exist (so the deployed app never regresses). `updated_at` becomes the
   real max `captured_on` (ISO date string in JSON — response shape
   otherwise unchanged). **Contract addition #1** (needs §5 update):
   `updated_at` now reflects actual data date, not the hardcoded mock
   date.
5. **Trends endpoint.** **Contract addition #2**: propose
   `GET /api/v1/housing/trends` returning per-district point series
   ordered by `captured_on` (shape drafted by you, finalized at review).
   Thin route, math/logic in the service.
6. **Tests.** SQLite-compatible pytest (existing override pattern):
   fallback ordering, double-ingest idempotency, trends shape, 503-on-no-
   db behavior unchanged, health/taxes unaffected.

## Non-goals

- No frontend changes (trend UI is a follow-up task).
- No scrapers/cron hitting third-party sites; no new Python dependencies
  beyond the standard library unless cleared at review.
- No other cities beyond the `city` column being future-ready.
- Do not modify `district_rents`, the seed, or the taxes code paths.

## Acceptance criteria

- [ ] pytest green including new tests; live check with compose Postgres:
      ingest twice → row count does not grow;
      `GET /api/v1/housing/rents` returns snapshot-backed values with the
      real `updated_at`; `GET /api/v1/housing/trends` returns the series;
      `docker compose stop db` → housing still 503, others 200.
- [ ] Empty-snapshot DB behaves exactly like today (fallback verified).
- [ ] `SOURCES.md` cites a concrete public source with a retrieval date.
- [ ] The imported snapshot contains fresh, source-backed values; no
      `mock-carryover` rows are accepted as task completion.
- [ ] `git diff` scope: backend models/services/routes/schemas/scripts/
      tests + `backend/scripts/data/*`. No frontend files.

## Verification

- `cd backend && pytest` (SQLite) and a live uvicorn run against compose
  db as in CONTEXT §7.
- Commits: `feat(housing): rent snapshot model and idempotent ingest` +
  `feat(api): snapshot-backed rents and trends endpoint` (or one commit
  if cleaner).

## On completion

Set T15 to `[R]` in `TODO.md` + a journal entry; list both contract
additions explicitly for the orchestrator's CONTEXT §5 update.
