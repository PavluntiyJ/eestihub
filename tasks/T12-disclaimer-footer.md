# T12 — Calculator disclaimer + site footer

**Read first:** `docs/CONTEXT.md` (§4, §6).
**Dependencies:** T06, T07 accepted. **Role:** Frontend (TS/React).
**Branch:** `feat/t12-disclaimer` off current `main`; before handing
off — `git rebase main` (T10 runs in `main` in parallel; no overlap, but
same procedure). The orchestrator merges after review.

## Goal

Before going public the site must be honest about what it is not: the
calculator is not tax advice, the housing data is demo data. Plus a
site-wide footer carrying that note and a GitHub link.

## Steps

0. **Brand rename EstiHub → EestiHub** (owner's decision, matches the
   repo name and correct Estonian): every occurrence in
   `src/messages/{en,et,ru}.json` (header brand, metadata titles, hero
   copy) and the FastAPI title in `backend/app/main.py`
   (`"EstiHub API"` → `"EestiHub API"` — this one line is an explicit
   exception to the backend non-goal below). Do NOT rename
   infrastructure identifiers (`estihub` DB user/database in
   docker-compose and `.env.example` stay as they are).
1. A disclaimer on the calculator page (`/[locale]/calculator`), Server
   Component, below the form/results: the calculation is an estimate and
   not tax or legal advice; rates are Estonia 2026; verify decisions
   with EMTA. Link to https://www.emta.ee
   (`rel="noopener noreferrer"`, `target="_blank"`).
2. A note on the housing page: the data is demo (mock) data and does not
   reflect the real market. Visible but not shouting (muted text under
   the title or in the Dataset status card).
3. `src/components/site-footer.tsx` — Server Component, mounted in the
   layout: © {current year} EestiHub · a short disclaimer line · a link
   to the GitHub repository (github.com/PavluntiyJ/eestihub) · a link to
   EMTA. No navigation, no social icons.
4. All strings — a `footer` namespace plus additions to
   `calculator`/`housing` in `src/messages/{en,et,ru}.json`; careful
   et/ru translations (legal wording in plain language, no legalese).
5. Verification: prod build, all three locales, the e2e suite still
   passes (`npm run e2e` with the backend up — 6 passed).
6. Commit: `feat(frontend): calculator disclaimer, mock-data note and site footer`.

## Non-goals

- Do not change the calculator form, api client, backend (except the
  single FastAPI title line from step 0), or `.github/`.
- No cookie banners, analytics, or terms-of-service — only the
  disclaimer.
- No new dependencies and no `any`.

## Acceptance criteria

- [ ] `npm run build` clean; `npm run e2e` → 6 passed (do not modify the
      tests; if the footer breaks a locator, that's a signal to fix the
      locator T09-style — write it to the orchestrator notes).
- [ ] `/en|et|ru/calculator` shows a translated disclaimer with the EMTA
      link.
- [ ] `/en|et|ru/housing` shows a translated mock-data note.
- [ ] The footer is on every page: ©, the disclaimer line, GitHub/EMTA
      links; Server Component, no `'use client'`.
- [ ] Dictionary keys symmetric across en/et/ru.

## On completion

Set T12 to `[R]` in `TODO.md` + a journal entry (what was verified and how).
