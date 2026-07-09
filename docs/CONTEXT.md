# CONTEXT.md — project architecture context

> This file is the single source of truth for all AI workers.
> Read it IN FULL before executing any task from `tasks/`.
> Only the orchestrator (Tech Lead) may edit this file.

## 1. What we are building

**EstiHub** (working title) — an interactive web service for expats and
entrepreneurs in Estonia. Goals: high performance, SEO, clean
architecture (the project goes into a portfolio/CV).

MVP — two features:
1. **Tax calculator** — net-income comparison across 4 regimes:
   Tööleping (employment contract), Juhatuse liige (management board
   member), FIE (sole proprietor), Ettevõtluskonto (entrepreneur
   account).
2. **Housing rent dashboard** — average rent prices by Tallinn
   district, API + interactive visualization.

## 2. Stack (fixed, do not change)

| Layer     | Technology |
|-----------|-----------|
| Frontend  | Next.js 15 (App Router), TypeScript strict, Tailwind CSS, shadcn/ui |
| Charts    | Recharts — only via shadcn/ui chart components, client leaf components |
| E2E       | Playwright (`@playwright/test`, chromium only), tests in `frontend/e2e/` |
| Backend   | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.x |
| DB        | PostgreSQL 16 (Docker) |
| Dev env   | Docker Compose (Postgres only for now; frontend and backend run locally) |

## 3. Repository structure (monorepo)

```
new_site_project/
├── frontend/                  # Next.js 15
│   └── src/
│       ├── app/               # App Router: pages = Server Components
│       ├── components/ui/     # shadcn/ui (CLI-generated)
│       ├── features/          # features: tax-calculator/, housing/
│       │   └── <feature>/     #   components/, hooks/, api.ts
│       ├── lib/               # utilities, api client
│       └── types/             # types mirroring Pydantic schemas
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app factory, CORS, routers
│   │   ├── core/config.py     # settings (pydantic-settings), env
│   │   ├── core/tax_rates.py  # tax rates — ONLY here
│   │   ├── api/v1/routes/     # thin routes: health.py, taxes.py, housing.py
│   │   ├── schemas/           # Pydantic v2 request/response schemas
│   │   ├── services/          # business logic: tax_service.py, housing_service.py
│   │   └── models/            # SQLAlchemy models
│   ├── scripts/               # maintenance scripts (housing seed)
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── docker-compose.yml         # postgres (+ backend/frontend later)
├── docs/CONTEXT.md            # this file
├── tasks/                     # task briefs for workers
├── TODO.md                    # task board and journal
└── CLAUDE.md
```

## 4. Code rules (mandatory for every task)

- **No `any`** in TypeScript. `tsconfig` strict.
- FastAPI routes are thin: validation + service call. All math lives in
  `services/`.
- Server Components by default; `'use client'` only for interactivity
  (forms, charts, local state).
- TS types in `frontend/src/types/` must match backend Pydantic schemas
  1:1 (snake_case field names as in the API).
- Code, identifiers, comments, commits — **in English** (portfolio
  project). Comment only non-obvious architectural decisions.
- Tax rates/constants — only in `backend/app/core/tax_rates.py`,
  no magic numbers in services.
- Every endpoint lives under the `/api/v1/` prefix.
- All project documentation (docs, briefs, TODO) is in English.

## 5. API contract (v1)

### GET /api/v1/health
Response `200`: `{ "status": "ok" }`

### POST /api/v1/calculate-taxes
Request:
```json
{
  "gross_monthly_income": 3000.0,
  "pension_pillar_rate": 0.02
}
```
- `gross_monthly_income`: float > 0 — gross monthly income, EUR.
- `pension_pillar_rate`: 0.0 | 0.02 | 0.04 | 0.06 (II pension pillar; default 0.02).

Response `200` — comparison across all 4 regimes:
```json
{
  "input": { "gross_monthly_income": 3000.0, "pension_pillar_rate": 0.02 },
  "results": [
    {
      "regime": "tooleping",
      "label": "Employment contract (Tööleping)",
      "employer_total_cost": 4014.0,
      "gross_income": 3000.0,
      "breakdown": [
        { "name": "income_tax", "amount": 462.0 },
        { "name": "unemployment_insurance_employee", "amount": 48.0 },
        { "name": "pension_pillar_ii", "amount": 60.0 }
      ],
      "net_income": 2430.0,
      "effective_tax_rate": 0.395
    }
  ]
}
```
- `regime`: `"tooleping" | "juhatuse_liige" | "fie" | "ettevotluskonto"`.
- `effective_tax_rate` = 1 − net_income / employer_total_cost.
- Numbers in the example are illustrative; calculation precision — 2
  decimal places (Decimal, standard ROUND_HALF_UP).

### Tax logic (Estonia, 2026 — rates VERIFIED against emta.ee)
Values for `tax_rates.py` (T03 worker verified against current data and
recorded sources in comments):
- Income tax: 22%.
- Basic exemption: €700/month (universal from 2026).
- Social tax: 33% (paid by the employer; FIE pays it themselves).
- Unemployment insurance: 1.6% employee + 0.8% employer (tööleping only).
- II pension pillar: 2/4/6% (tööleping; not applied to juhatuse liige
  by default).
- Juhatuse liige: 22% income tax + 33% social tax, NO unemployment
  insurance.
- FIE: 33% social tax on net income (simplified, no cap in the MVP),
  then 22% income tax.
- Ettevõtluskonto (verified by the orchestrator on emta.ee 2026-07-09):
  the 40% rate was ABOLISHED on 2025-01-01. Base rate — 20% of receipts;
  for II pension pillar members the rate is higher: 22% / 24% / 26%
  for 2% / 4% / 6% contributions respectively (i.e. 20% +
  pension_pillar_rate). Above €40,000/year of receipts the person must
  register as an entrepreneur (reference fact only in the MVP, not used
  in the calculation). No other taxes.

### GET /api/v1/housing/rents
Response: Tallinn districts served from Postgres (seeded data):
```json
{
  "city": "Tallinn",
  "updated_at": "2026-07-01",
  "districts": [
    { "name": "Kesklinn", "avg_rent_1room": 550, "avg_rent_2room": 750,
      "avg_rent_3room": 950, "avg_utilities": 180, "lat": 59.437, "lon": 24.745 }
  ]
}
```
Returns 503 when the database is unavailable or not seeded.

## 6. Internationalization (i18n) — hard requirement

The site is trilingual: **English (en, default), Estonian (et), Russian (ru)**.

- Library: **next-intl** (App Router-native, SSR/SEO-friendly).
- Locale-prefixed routing: `/{locale}/...` → `src/app/[locale]/...`
  structure; next-intl middleware redirects `/` → `/en` and detects the
  locale.
- Dictionaries: `frontend/src/messages/{en,et,ru}.json`. No hardcoded
  user-facing strings in components — translation keys only.
- SEO: `hreflang` alternates in metadata, `lang` on `<html>` per locale.
- Language switcher — in the header (client leaf component).
- The backend API is locale-neutral: it returns machine keys/numbers
  (`regime: "tooleping"`); human-readable labels come from the frontend
  dictionaries. The `label` field in API responses is service/debug
  data — never use it in the UI.

## 7. Local development (after T01–T02)

```bash
docker compose up -d db                      # Postgres on :5432
cd backend && python -m scripts.seed_housing # seed housing data (after T08)
cd backend && uvicorn app.main:app --reload  # API on :8000
cd frontend && npm run dev                   # UI on :3000
cd frontend && npm run e2e                   # e2e smokes (needs API on :8000; after T09)
```
CORS: the backend allows `http://localhost:3000`.
The frontend reaches the backend via `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
The backend reaches Postgres via `DATABASE_URL` (default — the compose DB, see `backend/.env.example`).
