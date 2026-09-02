# T16 — e-Residency first-year cost calculator

**Read first:** `docs/CONTEXT.md` (§2, §4–§6).
**Dependencies:** none. **Role:** Full-stack (small vertical slice).
**Branch:** work in `main`.

## Context

EestiHub targets expats and entrepreneurs; e-Residency is the top-funnel
topic for that audience (global search demand, little tool competition).
This task adds a trilingual calculator: "What does an e-resident OÜ cost
in year one?" — setup costs, monthly running costs, first-year total, and
the monthly revenue needed to break even. Tax-interplay modeling
(dividends vs salary optimization) is deliberately out of scope; this is
an honest, verifiable cost estimator.

## Steps

1. **Verify the inputs (mandatory, T03 discipline).** Check current
   figures against primary sources: e-residency state fee and renewal
   (e-residency.gov.ee), OÜ formation options (self-service via the
   commercial register vs notary), legal address/contact person market
   rates, typical monthly accounting service ranges. Record every constant
   with its source and retrieval date.
2. **Backend constants.** `backend/app/core/fees.py` — all money
   constants with source comments (same rules as `tax_rates.py`; no
   magic numbers in services).
3. **API.** `POST /api/v1/calculate-eresidency` under the v1 prefix:
   - request: `{ "expected_monthly_revenue": float > 0 }` (+ optionally
     `monthly_accounting_fee: float >= 0` defaulting to the fee-table
     midpoint);
   - response: `{ input, setup_breakdown: [{name, amount}],
     monthly_running_cost, first_year_total_cost,
     break_even_monthly_revenue, first_year_revenue,
     first_year_surplus }`;
   - `break_even_monthly_revenue` = `first_year_total_cost / 12` rounded
     up to whole euros (Decimal, ROUND_HALF_UP per house convention);
   - `first_year_revenue` = `expected_monthly_revenue * 12` and
     `first_year_surplus` = `first_year_revenue - first_year_total_cost`;
   - business logic in `services/eresidency_service.py`, thin route,
     Pydantic v2 schemas, pytest with manual derivations.
   **Contract addition** — the orchestrator reviews it into CONTEXT §5.
4. **Frontend.** `/[locale]/eresidency` page: Server Component shell +
   metadata/hreflang per locale; client leaf form following the
   calculator-form pattern; result cards; disclaimer linking the official
   e-Residency portal (`rel="noopener noreferrer"`). Feature folder
   `features/eresidency/` mirroring `tax-calculator/` structure.
5. **Navigation + SEO plumbing.** One nav entry in `site-nav.tsx`
   (`nav.eresidency` key); add the page to `sitemap.ts` (3 locales →
   sitemap grows 9 → 12 URLs); new `eresidency` namespace symmetric in
   `messages/{en,et,ru}.json`.
   **Added 2026-09-02:** you are the sole owner of `sitemap.ts` this
   iteration, so also add `x-default` to its `alternates` and a
   `lastModified` on every entry while you are in the file. T18 gave up
   that change to avoid a conflict with you. Note that T18 is setting
   `metadataBase` in the locale layout in parallel — do not add one
   yourself, and write your page's `alternates` as relative paths exactly
   like the existing pages do.
6. **e2e smoke.** Nav link → page renders → submit a valid revenue → a
   result figure is visible.

## Non-goals

- No dividends-vs-salary tax optimization, no II-pillar interplay
  (backlog).
- No PDF/export, no multi-year projection, no currency conversion.
- No changes to housing or existing calculator features; do not touch
  `tax_rates.py` or the taxes routes.

## Acceptance criteria

- [ ] pytest green incl. derivations; constants traceable to cited
      sources in `fees.py`.
- [ ] Live API: valid request → 200 with all fields; invalid input → 422.
- [ ] `npm run build` passes; `/en|et|ru/eresidency` render translated
      with correct hreflang; sitemap has 12 URLs with alternates.
- [ ] `npm run e2e` passes including the new smoke.
- [ ] `'use client'` only inside `features/eresidency/` (+ pre-existing
      client leaves); no `any`.

## Verification

- `cd backend && pytest`; uvicorn + curl checks per CONTEXT §7.
- `cd frontend && npm run build && npm run e2e` (backend up, db seeded).
- Commits: `feat(api): e-residency cost endpoint` +
  `feat(frontend): e-residency calculator page` (or one commit if
  cleaner).

## On completion

Set T16 to `[R]` in `TODO.md` + a journal entry; flag the API-contract
addition for the CONTEXT §5 update.
