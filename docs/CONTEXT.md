# CONTEXT.md — project architecture context

> This file is the single source of truth for all AI workers.
> Read it IN FULL before executing any task from `tasks/`.
> Only the orchestrator (Tech Lead) may edit this file.

## 1. What we are building

**EestiHub** (working title) — an interactive web service for expats and
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
Response: `{ "status": "ok" | "degraded", "database": "ok" | "unavailable" }`

The endpoint executes a real `SELECT 1`, so it can fail. Status codes:
- `200` + `{"status": "ok", "database": "ok"}` — process and database both up.
- `503` + `{"status": "degraded", "database": "unavailable"}` — the query
  failed.

Returning 503 on a database fault is deliberate: `render.yaml` points
`healthCheckPath` here, so a real dependency outage is visible to the
platform. Endpoints that do not touch the database (taxes, e-Residency)
keep returning `200` while health is degraded — health reports the
dependency, it does not gate unrelated features.

### POST /api/v1/calculate-taxes
Request:
```json
{
  "gross_monthly_income": 3000.0,
  "pension_pillar_rate": 0.02,
  "equalize_by": "gross"
}
```
- `gross_monthly_income`: float > 0 — EUR per month. Its meaning depends
  on `equalize_by` (see below).
- `pension_pillar_rate`: 0.0 | 0.02 | 0.04 | 0.06 (II pension pillar; default 0.02).
- `equalize_by`: `"gross" | "payer_cost"`, default `"gross"` — the basis
  on which the four regimes are made comparable (see "Comparison basis").

Response `200` — comparison across all 4 regimes:
```json
{
  "input": {
    "gross_monthly_income": 3000.0,
    "pension_pillar_rate": 0.02,
    "equalize_by": "gross"
  },
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
      "effective_tax_rate": 0.395,
      "constraints": []
    },
    {
      "regime": "ettevotluskonto",
      "label": "Entrepreneur account (Ettevõtluskonto)",
      "employer_total_cost": 3000.0,
      "gross_income": 3000.0,
      "breakdown": [
        { "name": "business_income_tax", "amount": 660.0 }
      ],
      "net_income": 2340.0,
      "effective_tax_rate": 0.22,
      "constraints": [
        { "code": "vat_registration_threshold_exceeded", "severity": "warning" }
      ]
    }
  ]
}
```
- `regime`: `"tooleping" | "juhatuse_liige" | "fie" | "ettevotluskonto"`.
- `employer_total_cost` — total monthly cost to the **payer**: the employer
  for `tooleping`/`juhatuse_liige`, the client for `fie`/`ettevotluskonto`.
  The field name is kept for contract stability; the meaning is "payer cost".
- `effective_tax_rate` = 1 − net_income / employer_total_cost.
- `constraints` — statutory limits hit by this result, always present,
  possibly empty. Machine keys only (§6): the UI renders them from the
  dictionaries. `severity`: `"info" | "warning" | "blocker"`.
  Defined codes:
  - `ettevotluskonto_annual_limit_exceeded` (`blocker`) — receipts × 12
    exceed the €40,000 registration threshold.
  - `vat_registration_threshold_exceeded` (`warning`) — turnover × 12
    exceeds the €40,000 VAT threshold. `fie` and `ettevotluskonto` only.
  - `fie_social_tax_minimum_applied` (`info`) — the statutory monthly
    minimum was used instead of 33% of income.
  - `fie_social_tax_cap_applied` (`info`) — the annual ceiling was used
    instead of 33% of income.
- Numbers in the example are illustrative; calculation precision — 2
  decimal places (Decimal, standard ROUND_HALF_UP).

### Comparison basis (`equalize_by`)
The four regimes cost the payer different amounts for the same gross, so a
single number cannot rank them. Both bases are legitimate and the API
supports both; the UI must let the user choose and must label which one is
active.

- `"gross"` — every regime is computed from the same
  `gross_monthly_income`. The historical behaviour.
- `"payer_cost"` — `gross_monthly_income` is read as the total monthly
  cost to the payer, and each regime derives the gross that produces
  exactly that cost:
  - `tooleping`: gross = cost / (1 + social_tax + unemployment_employer)
  - `juhatuse_liige`: gross = cost / (1 + social_tax)
  - `fie`, `ettevotluskonto`: gross = cost

In both cases `employer_total_cost` and `gross_income` in the response
report the actual figures used for that regime.

### Tax logic (Estonia, 2026 — rates VERIFIED against emta.ee)
Values for `tax_rates.py` (T03 worker verified against current data and
recorded sources in comments):
- Income tax: 22%.
- Basic exemption: €700/month (universal from 2026).
- Social tax: 33% (paid by the employer; FIE pays it themselves).
- Unemployment insurance: 1.6% employee + 0.8% employer (tööleping only).
- II pension pillar: 2/4/6%. Withheld from **both** tööleping and
  juhatuse liige (see the correction below).
- Juhatuse liige: 22% income tax + 33% social tax (employer), NO
  unemployment insurance, **II pension pillar contribution IS withheld**
  at `pension_pillar_rate` for anyone enrolled. The income tax base is
  gross − pension contribution − basic exemption.
  CORRECTED 2026-09-02 by the orchestrator: this file previously stated
  the contribution was not applied to juhatuse liige, and the T03
  implementation followed that. It was wrong — only unemployment
  insurance is exempt for a board member. See audit finding F-01.
- FIE: 33% social tax on business income, **bounded on both sides**:
  - lower bound — the statutory monthly minimum obligation
    (social tax monthly rate `kuumäär` × 33%). Owed regardless of income.
  - upper bound — the statutory annual ceiling, divided by 12 for the
    monthly model.
  Then 22% income tax on (business income − social tax − basic exemption).
  Both bounds must be traceable to emta.ee in `tax_rates.py` comments and
  re-verified at implementation time (the 2026 `kuumäär` moved to €886;
  the annual ceiling is derived from the minimum wage). The MVP's
  unbounded 33% was a documented simplification and is now retired —
  see audit finding F-03.
- VAT registration threshold: €40,000 of annual taxable turnover.
  Reference constant, surfaced through `constraints`, never used in the
  net-income arithmetic.
- Ettevõtluskonto (verified by the orchestrator on emta.ee 2026-07-09):
  the 40% rate was ABOLISHED on 2025-01-01. Base rate — 20% of receipts;
  for II pension pillar members the rate is higher: 22% / 24% / 26%
  for 2% / 4% / 6% contributions respectively (i.e. 20% +
  pension_pillar_rate). Above €40,000/year of receipts the person must
  register as an entrepreneur — surfaced through the
  `ettevotluskonto_annual_limit_exceeded` constraint, never used in the
  net-income arithmetic. No other taxes.

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

`updated_at` is the real maximum `captured_on` across the snapshots
actually served — not a hardcoded date. Values come, per district, from
the most recent `rent_snapshots` row, falling back to the legacy
`district_rents` row when a district has no snapshot. `avg_utilities` is
not published by the rent source, so it always comes from the legacy row.

The response carries `Cache-Control: public, max-age=86400,
stale-while-revalidate=604800` — rent data changes monthly at best and
this endpoint is the one database read on the hot path.

### GET /api/v1/housing/trends
Per-district rent history, oldest point first:
```json
{
  "city": "Tallinn",
  "districts": [
    {
      "name": "Kesklinn",
      "points": [
        { "captured_on": "2026-05-27", "avg_rent_1room": 825,
          "avg_rent_2room": 1125, "avg_rent_3room": 1650,
          "avg_utilities": null, "source": "https://..." }
      ]
    }
  ]
}
```
- Districts are ordered by name, points ascending by `captured_on`.
- `avg_utilities` is nullable here — the snapshot source does not publish
  it, and the API reports that honestly rather than substituting the
  legacy estimate.
- `source` is the citation URL carried on the snapshot row.
- Returns 503 on the same conditions as `/housing/rents`.

### POST /api/v1/calculate-eresidency
Request:
```json
{ "expected_monthly_revenue": 4000.0, "monthly_accounting_fee": 75.0 }
```
- `expected_monthly_revenue`: float > 0, EUR per month.
- `monthly_accounting_fee`: float ≥ 0, defaults to the midpoint of the
  fee table in `backend/app/core/fees.py`.

Response `200`:
```json
{
  "input": { "expected_monthly_revenue": 4000.0, "monthly_accounting_fee": 75.0 },
  "setup_breakdown": [
    { "name": "eresidency_application", "amount": 150.0 },
    { "name": "ou_online_registration", "amount": 265.0 },
    { "name": "contact_person_first_year", "amount": 300.0 }
  ],
  "monthly_running_cost": 75.0,
  "first_year_total_cost": 1615.0,
  "break_even_monthly_revenue": 135.0,
  "first_year_revenue": 48000.0,
  "first_year_surplus": 46385.0
}
```
- `break_even_monthly_revenue` = `first_year_total_cost / 12`, rounded to
  whole euros (Decimal, ROUND_HALF_UP).
- `setup_breakdown` names are machine keys (§6); the UI labels them from
  the dictionaries.
- This is a **cost** model only. It deliberately does not model tax on
  revenue — dividends-vs-salary optimisation is backlog, and the page
  must not imply the surplus is post-tax.
- Money constants live only in `backend/app/core/fees.py` with source
  URLs and retrieval dates, under the same rule as `tax_rates.py` (§4).

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
