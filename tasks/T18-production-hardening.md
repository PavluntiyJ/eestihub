# T18 — Production hardening: DB resilience, real health check, static rendering, absolute SEO URLs

**Read first:** `docs/CONTEXT.md` (§2–§7), `docs/DEPLOY.md`.
**Dependencies:** none. **Role:** Full-stack (infrastructure, no feature work).
**Branch:** work in `main`.
**Runs in parallel with:** T15, T16, T17. Stay inside "Files you own".

## Context

The app is deployed on Neon (compute autosuspends) behind Render Free
(service idles after 15 minutes), and nothing in the code accounts for
either. An orchestrator audit found five production defects. None of
them is visible locally, which is why the test suite is green and the
site still misbehaves.

- **F-05** `create_engine()` is called with a URL and nothing else. After
  an idle window SQLAlchemy hands out a dead connection, which surfaces
  as `OperationalError` → 503 from `/housing/rents` → "data unavailable"
  on the dashboard until someone reloads.
- **F-06** `/api/v1/health` returns a literal. Render's
  `healthCheckPath` stays green with the database gone, and the landing
  page's status badge reads "online" while housing is dark.
- **F-07** No `metadataBase`, so canonical and hreflang ship as relative
  paths. Confirmed in a production build's HTML:
  `<link rel="canonical" href="/en"/>` and
  `<link rel="alternate" hrefLang="et" href="/et"/>`. Google requires
  fully-qualified URLs for hreflang annotations — the trilingual SEO the
  README leads with is not actually wired.
- **F-08** `fetchJson` calls `fetch` with no timeout, and the landing
  page carries `export const dynamic = "force-dynamic"` purely to render
  an API status badge. DEPLOY.md documents a ~1 minute Render cold start;
  that cold start is currently the landing page's time to first byte.
- **F-09** The production build marks every content route `ƒ`
  (server-rendered on demand). There is no `generateStaticParams` and no
  `setRequestLocale`, so next-intl cannot opt any page into static
  rendering and no HTML is CDN-cacheable.

## Steps

1. **F-05 — connection resilience.** `pool_pre_ping=True` and a
   `pool_recycle` short enough for Neon's idle behaviour, in
   `backend/app/core/db.py`. While in there: the engine is constructed at
   module import, so a malformed `DATABASE_URL` takes down the import
   rather than one request. Build it lazily (module-level accessor with
   `lru_cache`, mirroring `get_settings()`), keeping `get_session()`'s
   signature and the existing dependency-override pattern in the tests
   intact.

2. **F-06 — a health check that can fail.** `/api/v1/health` executes a
   trivial query (`SELECT 1`) and reports the database separately from
   the process:
   `{"status": "ok" | "degraded", "database": "ok" | "unavailable"}`.
   Return `200` when the process is up and `503` only when the database
   is down, so Render restarts the service on a real fault and not on a
   Neon cold start — decide which, justify it in the journal, and keep
   `render.yaml`'s `healthCheckPath` working either way.
   **Contract addition** — `HealthResponse` gains a field; the
   orchestrator mirrors it into CONTEXT §5 at review. Update
   `frontend/src/types/api.ts` to match 1:1 and
   `backend/tests/test_health.py`.

3. **F-08 — timeouts and an unblocked landing page.** Add a default
   `AbortSignal.timeout()` to `fetchJson` in `frontend/src/lib/api.ts`,
   overridable per call. Then remove `export const dynamic =
   "force-dynamic"` from `app/[locale]/page.tsx`: move the status badge
   into a small client leaf that fetches after hydration and renders a
   neutral "checking" state first. The page must render fully with the
   backend down, and must not wait on it.

4. **F-09 — static rendering.** Add `generateStaticParams()` returning
   the three locales, and call next-intl's `setRequestLocale(locale)` at
   the top of every page and of the locale layout. `/[locale]` and
   `/[locale]/calculator` must build as static. `/[locale]/housing`
   fetches live data — keep it dynamic, but give the fetch an explicit
   `revalidate` rather than `cache: "no-store"`, since rent data changes
   monthly at best. Verify against the route table in `npm run build`
   output and paste it into the journal entry.

5. **F-07 — absolute URLs.** Set `metadataBase` from
   `NEXT_PUBLIC_SITE_URL` in the root of the locale layout's metadata.
   Confirm with a production build that canonical and every hreflang
   emit as absolute URLs.
   Do **not** touch `sitemap.ts` — T16 is editing it in parallel and
   carries the `x-default` and `lastModified` additions.

6. **Response caching on the rents endpoint.** `/api/v1/housing/rents`
   serves data that changes monthly and hits Postgres on every request.
   Add a `Cache-Control` header with a sensible `max-age` and
   `stale-while-revalidate`. No caching library, no new dependency.

7. **F-17 — dependency split.** Move `pytest` and `httpx` out of
   `backend/requirements.txt` into `backend/requirements-dev.txt`, and
   update the two CI jobs that install them plus `docs/DEPLOY.md` if it
   names the file. Render's build command must stop installing test
   dependencies.

## Non-goals

- No ruff / mypy / pyproject migration (backlog).
- No dark mode, no font fix, no error boundaries, no OG images — T19
  owns `globals.css` and the metadata beyond `metadataBase`.
- No changes to tax or housing business logic; no changes under
  `features/`, `components/`, or `messages/`.
- No new backend dependencies.
- Do not touch `app/[locale]/eresidency/` if T16 has created it — merge
  around it and add `setRequestLocale` to it only if it already exists
  on `main` when you start.

## Files you own

`backend/app/core/db.py`, `backend/app/api/v1/routes/health.py`,
`backend/app/api/v1/routes/housing.py` (headers only),
`backend/app/schemas/health.py`, `backend/tests/test_health.py`,
`backend/requirements.txt`, `backend/requirements-dev.txt`,
`.github/workflows/ci.yml`, `render.yaml`, `docs/DEPLOY.md`,
`frontend/src/lib/api.ts`, `frontend/src/types/api.ts` (the
`HealthResponse` type only), `frontend/src/app/[locale]/layout.tsx`,
`frontend/src/app/[locale]/page.tsx`,
`frontend/src/app/[locale]/calculator/page.tsx` and
`frontend/src/app/[locale]/housing/page.tsx` (page shells only — not the
components they render), and one new client leaf for the status badge
under `frontend/src/components/`.

T17 owns `frontend/src/types/api.ts`'s tax types. Touch only
`HealthResponse` there, and say so in your journal entry so the
orchestrator can check the merge.

## Acceptance criteria

- [ ] `cd backend && pytest` green (installed from
      `requirements.txt` + `requirements-dev.txt`).
- [ ] `docker compose stop db` → `/api/v1/health` reports the database as
      unavailable; `/api/v1/calculate-taxes` still returns 200.
      `docker compose start db` → health recovers **without restarting
      uvicorn** (this is the `pool_pre_ping` proof; verify it explicitly).
- [ ] `/api/v1/housing/rents` returns a `Cache-Control` header.
- [ ] `frontend/src/app/sitemap.ts` is untouched (T16 owns it).
- [ ] `npm run build` route table shows `/[locale]` and
      `/[locale]/calculator` as static (`○`); paste the table into the
      journal.
- [ ] With `NEXT_PUBLIC_SITE_URL` set, the built HTML for `/en` contains
      absolute canonical and hreflang URLs. Quote one of each in the
      journal.
- [ ] Backend fully down: the landing page renders at 200 in under a
      second and shows the offline state; no page hangs on a cold API.
- [ ] `npm run e2e` passes unchanged.
- [ ] `git diff` touches no file outside "Files you own".

## Verification

- `cd backend && pytest`, plus the live compose stop/start cycle above.
- `cd frontend && NEXT_PUBLIC_SITE_URL=https://eestihub.vercel.app npm run build`,
  then `npm run start` and `curl` the emitted `<head>`.
- Commits: `fix(db): resilient pooling and lazy engine` +
  `feat(api): database-aware health check and cached rents` +
  `fix(seo): absolute canonical and hreflang, static locale rendering`.

## On completion

Set T18 to `[R]` in `TODO.md` + a journal entry. Flag the
`HealthResponse` contract addition explicitly for the CONTEXT §5 update,
and state which restart-policy choice you made in step 2 and why.
