# T05 — Housing API (mock data) + rent dashboard

**Read first:** `docs/CONTEXT.md` (§3, §4, §5 — the
`GET /api/v1/housing/rents` contract, §6 i18n, §7).
**Dependencies:** T03, T04 accepted. **Role:** Full-stack.
**Branch:** work directly in `master` (T06 runs in parallel on its own
branch — do not touch its files, see "Non-goals").

## Goal

A full vertical slice of the second feature: the backend serves mock
Tallinn district rent data per the §5 contract, the frontend shows a
dashboard (table + bar chart) at `/[locale]/housing` in three languages.

## Steps — backend

1. `app/services/housing_data.py` — mock data as a separate Python
   module (orchestrator's decision: a module, not JSON — typed, no IO;
   swapping in a real parser later only changes this module).
   8 districts: Kesklinn, Põhja-Tallinn, Kristiine, Mustamäe, Lasnamäe,
   Haabersti, Nõmme, Pirita. Fields per the §5 contract (`name`,
   `avg_rent_1room`, `avg_rent_2room`, `avg_rent_3room`,
   `avg_utilities`, `lat`, `lon`). Values — plausible for 2026
   (Kesklinn priciest, Lasnamäe cheapest); mark the module as mock in a
   comment with the date.
2. `app/schemas/housing.py` — Pydantic v2: `DistrictRent`,
   `HousingRentsResponse` (`city`, `updated_at` ISO date string,
   `districts`).
3. `app/services/housing_service.py` — a service assembling the response
   from `housing_data`. The route holds no math/data.
4. `app/api/v1/routes/housing.py` — thin `GET /api/v1/housing/rents`,
   mount into the v1 router.
5. Tests (`backend/tests/`): status 200, response shape matches the
   schema, exactly 8 districts, all fields present, prices > 0,
   `avg_rent_1room < avg_rent_3room` for every district.

## Steps — frontend

6. `src/types/api.ts` — add `DistrictRent`, `HousingRentsResponse`
   (snake_case, 1:1 with the schemas). Do not modify existing types.
7. `src/lib/api.ts` — add `getHousingRents()`; do not reformat existing
   code.
8. Chart dependency: `recharts` via the shadcn/ui chart component
   (`npx shadcn@latest add chart`). Orchestrator's decision: Recharts is
   the shadcn/ui standard. No other new dependencies.
9. Page `src/app/[locale]/housing/page.tsx` — **Server Component**:
   server-side fetch (`cache: 'no-store'`); with the backend down show a
   graceful "data unavailable" state (the page must not crash). Feature
   components live in `src/features/housing/components/`:
   - district table (shadcn table): all contract columns, no lat/lon;
   - bar chart of average prices by district (`avg_rent_2room`) — a
     client leaf component (`'use client'` only there).
10. i18n: a `housing` namespace in `src/messages/{en,et,ru}.json` — page
    title, column labels, states. District names are proper nouns, do
    not translate. Page metadata (`generateMetadata`): localized
    title/description + hreflang (following the layout's pattern).
11. Commits (2, conventional): `feat(backend): housing rents mock api`,
    then `feat(frontend): tallinn rent dashboard`.

## Non-goals

- Do not touch: `site-header.tsx`, the calculator page and
  `src/features/tax-calculator/` (parallel T06), existing dictionary
  keys, backend tax code.
- Do not add header navigation links (that is a separate T07).
- No `any`, no DB/SQLAlchemy — the data is mock, Postgres is not needed.

## Acceptance criteria

- [ ] `pytest` green (including the new housing tests).
- [ ] `curl localhost:8000/api/v1/housing/rents` → 200, 8 districts, §5 shape.
- [ ] `npm run build` passes with no type or ESLint errors.
- [ ] `/en/housing`, `/et/housing`, `/ru/housing` open with translated
      strings; the table and bar chart show 8 districts.
- [ ] Backend stopped → the housing page shows the "unavailable" state,
      not a 500.
- [ ] `'use client'` — only in the chart component (and the previously
      accepted language-switcher).
- [ ] Types in `types/api.ts` match the backend schema field names.

## On completion

Set T05 to `[R]` in `TODO.md` + a journal entry (what was verified and how).
