# T06 — Tax calculator UI (form + regime comparison)

**Read first:** `docs/CONTEXT.md` (§4, §5 — the
`POST /api/v1/calculate-taxes` contract, §6 i18n, §7).
**Dependencies:** T03, T04 accepted. **Role:** Frontend (TS/React).
**Branch:** `feat/t06-calculator-ui` off current `master`. T05 (housing)
runs in `master` in parallel. Before handing off to `[R]` do
`git rebase master`; there should be no conflicts if the "Non-goals"
section is respected.

## Goal

A `/[locale]/calculator` page: income input form → POST to the backend →
clear net-income comparison across the 4 Estonian tax regimes, in three
languages. The backend contract is ready (T03) and does not change.

## Steps

1. `src/lib/api.ts` — add `calculateTaxes(request)` (POST, JSON body,
   `Content-Type: application/json`) on top of the existing `fetchJson`.
   Do not reformat existing code. Types come from `src/types/api.ts` —
   they already exist; do NOT modify that file.
2. Page `src/app/[locale]/calculator/page.tsx` — **Server Component**:
   title/description from dictionaries, localized `generateMetadata`
   (title/description + hreflang following the layout's pattern). The
   client form goes inside.
3. `src/features/tax-calculator/components/` — feature components:
   - `calculator-form.tsx` (`'use client'`): `gross_monthly_income`
     field (number, EUR, > 0), `pension_pillar_rate` select
     (0% / 2% / 4% / 6%, default 2%), submit. States: loading, API error
     (`ApiError` → a human-readable dictionary message), invalid input →
     submit disabled.
   - results: 4 regime cards (shadcn card) sorted by `net_income`
     descending: net income, total employer cost
     (`employer_total_cost`), effective rate (`effective_tax_rate`),
     expanded per-line breakdown.
   - comparison infographic: horizontal net-income bars (best regime =
     100% width), pure Tailwind — **no chart libraries and no new npm
     dependencies at all** (the parallel T05 installs recharts, do not
     duplicate).
4. Localization (a `calculator` namespace in
   `src/messages/{en,et,ru}.json`):
   - regime names come from dictionaries keyed by `regime`
     (`tooleping`, `juhatuse_liige`, `fie`, `ettevotluskonto`); do NOT
     render the API `label` field (CONTEXT §6);
   - breakdown line names come from dictionaries keyed by `name`; the
     full list the backend currently emits: `income_tax`,
     `unemployment_insurance_employee`, `pension_pillar_ii`,
     `social_tax`, `business_income_tax` (double-check against
     `backend/app/services/tax_service.py` before handing off);
   - format money and percentages with `Intl.NumberFormat` for the
     current locale (EUR, 2 decimals; percentages from fractions like
     0.395).
5. Manual check: with the backend up (uvicorn from `backend/`, venv)
   input €3000 / 2% → 4 cards, Tööleping net **2409.76**; with the
   backend down → error message, no page crash.
6. Commit: `feat(frontend): tax calculator ui with regime comparison`.

## Non-goals

- Do not touch: the backend entirely, `src/types/api.ts`,
  `site-header.tsx`, existing dictionary keys,
  `src/app/[locale]/page.tsx`, `src/features/housing/` (parallel T05).
- Do not add header navigation links (that is a separate T07).
- No new npm dependencies, no `any`, no hardcoded UI strings.

## Acceptance criteria

- [ ] `npm run build` passes with no type or ESLint errors.
- [ ] `/en/calculator`, `/et/calculator`, `/ru/calculator` — form and
      results fully translated (regimes, breakdown, errors).
- [ ] The €3000 / 2% calculation matches the API (Tööleping net
      2409.76); cards sorted by net income.
- [ ] Network/backend error → a clear message, no page crash.
- [ ] `page.tsx` is a Server Component; `'use client'` only in feature
      leaf components.
- [ ] The API `label` is rendered nowhere.
- [ ] Money/percentages formatted per locale (`Intl.NumberFormat`).
- [ ] Branch rebased onto current `master`, no conflicts.

## On completion

Set T06 to `[R]` in `TODO.md` + a journal entry (what was verified and
how); do not merge the branch — the orchestrator merges after review.
