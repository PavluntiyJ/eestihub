# T04 — Base Next.js page with a backend fetch

**Read first:** `docs/CONTEXT.md` (sections 3, 4, 5, 6 (i18n!), 7).
**Dependencies:** T02 accepted (needs a working /api/v1/health).
**Role:** Frontend (TS/React).

## Goal
A Next.js home page that polls the backend with a server-side fetch and
shows its status. Lay down the `lib/api-client`, `types/` and i18n
(en/et/ru) structure that features will build on.

## Steps

0. **i18n skeleton (next-intl)** per CONTEXT.md §6: `src/app/[locale]/`
   structure, middleware (default `en`, support `et`, `ru`),
   dictionaries `src/messages/{en,et,ru}.json`, language switcher in the
   header (client leaf component), `lang` on `<html>` and hreflang in
   metadata. All home page strings come from dictionaries; write the
   et/ru translations yourself (short marketing copy, translate
   carefully).
1. `src/lib/api.ts`: a small typed API client over `fetch` — base URL
   from `process.env.NEXT_PUBLIC_API_URL`, non-2xx handling (throw a
   typed error), JSON parsing. No axios, no extra wrappers.
2. `src/types/api.ts`: types mirroring the backend Pydantic schemas:
   `HealthResponse`, plus `TaxCalculationRequest/Response/RegimeResult/
   TaxLine` ahead of time per the CONTEXT.md §5 contract (keep
   snake_case field names).
3. Home page `src/app/page.tsx` — **Server Component**:
   - service hero block (name, one product paragraph, in English);
   - backend status: server-side fetch of `GET /api/v1/health`
     (`cache: 'no-store'`), online/offline badge via a shadcn/ui
     component (badge/card). Backend down → the page must not crash,
     it shows offline.
4. Base layout: `layout.tsx` with metadata (title, description for SEO),
   font via `next/font`.
5. Make sure `'use client'` appears nowhere without need.
6. Commit: `feat(frontend): base page with typed api client and backend status`.

## Non-goals
- No calculator or dashboard UI (T05/T06).
- No `any`, no third-party HTTP libraries.

## Acceptance criteria
- [ ] `npm run build` passes with no type or ESLint errors.
- [ ] With the backend running the page shows online; with it stopped —
      offline (verify both).
- [ ] `page.tsx` is a Server Component (no `'use client'`).
- [ ] Types in `types/api.ts` match the §5 contract field names.
- [ ] `/en`, `/et`, `/ru` open with translated content; `/` redirects
      to `/en`; the language switcher works; `lang` and hreflang
      alternates are correct in the HTML.

## On completion
Set T04 to `[R]` in `TODO.md` + a journal entry (what was verified and how).
