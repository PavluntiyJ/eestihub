# T09 — Playwright e2e smokes

**Read first:** `docs/CONTEXT.md` (§4, §6, §7).
**Dependencies:** T07 accepted. **Role:** Frontend/QA (TS).
**Branch:** `feat/t09-e2e` off current `master`; before handing off —
`git rebase master` (the backend task T08 runs in `master` in parallel,
no file overlap). The orchestrator merges after review.

## Goal

Browser smoke tests for the key user flows. Until now everything was
checked with curl against SSR HTML; clicks, hydration and the form's
client-side fetch are covered by nothing. After T09 every review runs
the e2e suite.

## Steps

1. Dependency: `@playwright/test` in devDependencies (the only new one).
   Browser — chromium only (`npx playwright install chromium`). If
   chromium fails to run in this environment (missing system
   libraries) — record the exact error in "Notes for the orchestrator"
   and hand the task off with that caveat instead of pulling in half the
   OS.
2. `frontend/playwright.config.ts`: `testDir: './e2e'`, `baseURL`
   `http://localhost:3000`, `webServer` — the prod frontend
   (`npm run build && npm run start`, `reuseExistingServer: true`).
   Tests do NOT start the backend: it must already run on :8000
   (uvicorn from `backend/`, venv) — document that precondition in a
   config comment. `package.json` script: `"e2e": "playwright test"`.
3. Tests in `frontend/e2e/` (TS strict, no `any`), scenarios:
   - **redirect+home**: `/` → `/en`, h1 visible, API badge online.
   - **language**: on `/en` click `ET` → URL `/et`, h1 switches to
     Estonian, `<html lang="et">`.
   - **navigation**: from `/en` click "Calculator" → `/en/calculator`,
     `aria-current` moves; click "Rent" → `/en/housing`.
   - **calculator (the key flow)**: on `/en/calculator` enter 3000,
     select 2%, submit → 4 regime cards appear, Tööleping net
     `€2,409.76` is visible along with the "best" badge on the top
     regime.
   - **housing**: on `/en/housing` the table has 8 district rows
     (Kesklinn … Pirita), the chart is rendered (canvas/svg present).
   - **invalid input**: clear the income field → submit is disabled and
     a validation message is shown.
   Locators — by role/aria/text (`getByRole`, `getByLabel`), not CSS
   classes.
4. Run the whole suite locally with the backend up; put the result
   (`N passed`) in the journal.
5. Commit: `test(frontend): playwright e2e smoke suite`.

## Non-goals

- Do not change production code (pages, components, dictionaries, api
  client). If a locator lacks aria/role support, write it to "Notes for
  the orchestrator" — do not patch components yourself.
- Do not touch the backend or `docker-compose.yml`.
- No other test frameworks, screenshot comparisons, or CI configs (CI is
  a separate next-iteration task).

## Acceptance criteria

- [ ] `npm run e2e` with the backend up: all scenarios green.
- [ ] The calculator scenario actually clicks submit and asserts on the
      response numbers (not just the form's presence).
- [ ] `npm run build` still clean; production code untouched (diff is
      only e2e/, config, package.json, lock).
- [ ] Locators are resilient (roles/aria/text), no CSS classes.
- [ ] Branch rebased onto current `master`.

## On completion

Set T09 to `[R]` in `TODO.md` + a journal entry (what was verified and
how, including the exact number of passing tests).
