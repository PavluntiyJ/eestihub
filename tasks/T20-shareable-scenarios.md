# T20 — Shareable calculator scenarios

**Read first:** `docs/CONTEXT.md` (§4–§6).
**Dependencies:** T17 (it rewrites the calculator form and adds
`equalize_by`), T14 (it adds the affordability panel to the same
component). Start only when both are `[R]` or later.
**Role:** Frontend. **Branch:** work in `main`.

## Context

Two audit findings that are one task, because fixing the first without
the second ships a bug.

- **F-15** The calculator's inputs live in `useState` and nowhere else.
  A user cannot bookmark a scenario, send one to an accountant, or come
  back to it — and the calculator page carries no indexable content
  beyond its hero, which is the one page on this site with real search
  demand behind it.
- **F-20** The language switcher links to `usePathname()`, which
  excludes search params and hash. Harmless today because no page has URL
  state; a guaranteed regression the moment F-15 is fixed.

This task is also the gate for a later programmatic-SEO iteration
(prerendered `/{locale}/salary/{amount}` pages). Design the URL contract
so that work does not have to redo it — but do not build those pages here.

## Steps

1. **URL contract.** Calculator state lives in the query string:
   `?gross=3000&pillar=2&basis=payer_cost`. Decide and document the exact
   parameter names and encodings in the brief's completion note — a
   later task will generate links against them. Notes on the shape:
   - `pillar` as whole percent (`0`, `2`, `4`, `6`) reads better in a
     URL than `0.02`; convert at the boundary;
   - `basis` mirrors the API's `equalize_by` values;
   - every parameter is optional and every one has the same default the
     form has today.

2. **Read on load, write on change.** The form initialises from the query
   string, validates it, and falls back to the current defaults for
   anything missing or malformed — a hand-typed junk URL must render the
   default form, never an error and never a blank page. Committed input
   changes push a new URL with `router.replace` (not `push`, so the back
   button does not walk through every keystroke) and without scrolling
   the page.

3. **Server-side first result.** With valid parameters present, the page
   shell fetches the calculation server-side and passes it to the form as
   initial state, so a shared link renders its numbers in the HTML rather
   than after a round trip. Keep the offline-tolerance rule: if the
   backend is unreachable the page still returns 200 with the form
   usable and the results area in its empty state.

4. **A copy-link control.** One button next to the results that copies
   the current URL, with a confirmation state. Text from the
   dictionaries.

5. **F-20 — preserve the query on locale switch.** The language switcher
   must carry search params (and hash) across the locale change. Verify
   with a populated calculator URL in all three locales.

6. **i18n.** Extend the existing `calculator` namespace for the copy
   control and its confirmation; keys symmetric across `en`/`et`/`ru`.

7. **e2e.** Two additions: opening `/en/calculator?gross=3000&pillar=2`
   directly renders results without a submit; switching locale from that
   URL lands on `/et/calculator` with the query intact and the results
   still shown.

## Non-goals

- No prerendered salary landing pages, no `generateStaticParams` for
  scenario URLs, no sitemap growth — a later task.
- No changes to the API. `equalize_by` and the constraint codes already
  exist from T17; this task only moves state into the URL.
- No changes to the housing feature or to any page shell other than
  `app/[locale]/calculator/page.tsx`.
- No new dependencies — `useSearchParams` and `URLSearchParams` are
  enough. Do not add a state-management or URL-state library.
- Do not restructure the affordability panel T14 added; read its inputs
  from the same state you now own.

## Files you own

`frontend/src/app/[locale]/calculator/page.tsx`,
`frontend/src/features/tax-calculator/`,
`frontend/src/components/language-switcher.tsx`,
the `calculator` namespace in `frontend/src/messages/*.json`,
`frontend/e2e/smoke.spec.ts`.

## Acceptance criteria

- [ ] `npm run build` passes; no `any`; no new dependency.
- [ ] `/en/calculator?gross=3000&pillar=2&basis=payer_cost` renders the
      results in the server HTML (check with `curl`, not just the
      browser) and the form reflects all three values.
- [ ] Changing any input updates the URL without a full navigation and
      without scroll jump; the back button returns to the previous
      committed scenario, not the previous keystroke.
- [ ] `?gross=abc&pillar=99` renders the default form at 200.
- [ ] Switching to `et` from a populated URL preserves every parameter.
- [ ] Backend down: the page is 200 and the form still works.
- [ ] `npm run e2e` passes including both new assertions.
- [ ] `git diff` touches no file outside "Files you own".

## Verification

- `cd frontend && npm run build && npm run start`, then `curl` a
  populated scenario URL and grep the HTML for a computed figure.
- `npm run e2e` (backend on :8000, db seeded).
- Commit: `feat(calculator): shareable scenario URLs`.

## On completion

Set T20 to `[R]` in `TODO.md` + a journal entry that **states the final
URL parameter contract verbatim** — names, encodings, defaults. The
programmatic-SEO task will be written against exactly what you record
there.
