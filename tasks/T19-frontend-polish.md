# T19 — Frontend polish: typeface, dark mode, error boundaries, OG images

**Read first:** `docs/CONTEXT.md` (§2, §4–§6).
**Dependencies:** T18 (it rewrites `app/[locale]/layout.tsx`; start after
T18 is `[R]` or later). **Role:** Frontend.
**Branch:** work in `main`.
**Runs in parallel with:** T14.

## Context

Four visible defects from the orchestrator audit, all cheap, all in the
first thing a reviewer sees.

- **F-10** Geist Sans is downloaded on every page and never applied.
  `globals.css` declares `--font-sans: var(--font-sans)` inside
  `@theme inline` — a variable defined as itself. The layout supplies
  `--font-geist-sans`, which nothing reads. Confirmed in the emitted
  stylesheet: the self-reference is invalid at computed-value time, so
  `body { @apply font-sans }` falls back to the browser default while
  the font files still load. `--font-mono` is wired correctly, which is
  why the figures look right and the prose does not.
- **F-11** `globals.css` carries a complete `.dark` token set and
  nothing anywhere sets that class or reads `prefers-color-scheme`.
- **F-13** No `error.tsx`, `not-found.tsx` or `loading.tsx` under
  `app/[locale]/`. A thrown render falls through to Next's default error
  page — in English, outside the site shell. The layout calls
  `notFound()` for an unknown locale and there is no localised page to
  receive it.
- **F-14** Open Graph metadata declares a title, description and type
  but no image, so every share of a portfolio project renders as a bare
  text link.

## Steps

1. **F-10 — wire the typeface.** Make `--font-sans` resolve to the font
   the layout actually loads. Verify in the built stylesheet that the
   self-reference is gone and that `body`'s computed `font-family`
   names Geist with a real fallback stack. Do not swap the typeface, and
   do not add a second font loader — the font is already there, it is
   the variable that is broken.

2. **F-11 — dark mode.** A theme control in the site header (client
   leaf), three states: light, dark, follow system. Persist the choice in
   `localStorage` and apply it before first paint so there is no flash —
   an inline script in the layout is the accepted pattern; keep it
   minimal and CSP-friendly. The existing `.dark` token block is the
   palette; do not redefine colours, and do not introduce a new
   dependency for this. Check every existing page in both themes,
   including the Recharts bar chart, whose colours come from
   `--chart-*`, and the `bg-[radial-gradient(...)]` hero backgrounds,
   which reference `--muted` directly.
   New `theme` namespace in `messages/{en,et,ru}.json`, keys symmetric.

3. **F-13 — boundaries.** Add `app/[locale]/error.tsx` (client, with a
   retry), `app/[locale]/not-found.tsx` and `app/[locale]/loading.tsx`.
   All three render inside the site shell and take their text from the
   dictionaries — new `errors` namespace, symmetric across locales.
   Confirm the layout's `notFound()` for an unknown locale reaches the
   localised page and does not 500.

4. **F-14 — OG images.** Generate them with `next/og` (part of Next, no
   new dependency): one route producing a per-locale card carrying the
   site name, the page title from the dictionaries and a restrained
   visual treatment consistent with the site. Wire it into
   `openGraph.images` and `twitter` metadata for all three page shells.
   Confirm the built HTML emits an absolute image URL — T18 set
   `metadataBase`, so this should follow from it; if it does not, say so
   rather than hardcoding a domain.

5. **Accessibility sweep on what you touched.** The theme control needs
   a visible focus state and an accessible name; the error page's retry
   must be reachable by keyboard. Respect `prefers-reduced-motion` in any
   transition you add.

## Non-goals

- No redesign. Same layout, same spacing, same components — this task
  fixes what is broken, it does not restyle what is not.
- No changes inside `features/tax-calculator/` or `features/housing/`
  beyond what a dark-theme fix strictly requires; T14 and T20 are working
  there. If a chart or panel needs a token change, do it in
  `globals.css`, not in the component.
- No new npm dependencies. `next/og` and `localStorage` are enough.
- No metadata changes beyond `openGraph`/`twitter` images — T18 owns
  `metadataBase`, canonical and hreflang.
- No analytics, no cookie banner.

## Files you own

`frontend/src/app/globals.css`,
`frontend/src/app/[locale]/error.tsx`,
`frontend/src/app/[locale]/not-found.tsx`,
`frontend/src/app/[locale]/loading.tsx`,
the OG image route under `frontend/src/app/`,
`frontend/src/components/site-header.tsx` and one new theme-control
component under `frontend/src/components/`,
the `openGraph`/`twitter` blocks of the three page shells under
`app/[locale]/`, and the new `theme` and `errors` namespaces in
`frontend/src/messages/*.json`.

## Acceptance criteria

- [ ] `npm run build` passes; no `any`; no new dependency in
      `package.json`.
- [ ] In the built CSS, `--font-sans` resolves to a real font stack and
      `body`'s computed font-family is Geist. Quote the rule in the
      journal.
- [ ] The theme control switches light/dark/system, survives a reload,
      and produces no flash of the wrong theme on first paint.
- [ ] All three pages are legible in dark mode in all three locales,
      including the housing chart and the hero gradients. Note anything
      that needed a token adjustment.
- [ ] Visiting `/xx` (an unsupported locale) renders the localised
      not-found page inside the site shell, not a Next default page.
- [ ] The built HTML for `/en`, `/et` and `/ru` each emit an absolute
      `og:image` URL, and the image route returns a valid PNG.
- [ ] `npm run e2e` passes unchanged.
- [ ] `git diff` touches no file outside "Files you own".

## Verification

- `cd frontend && npm run build && npm run start`, then inspect the
  emitted `<head>` and stylesheet with `curl`.
- Both themes checked in a real browser at desktop and mobile widths.
- `npm run e2e` (backend on :8000, db seeded).
- Commits: `fix(ui): apply the loaded sans typeface` +
  `feat(ui): theme control with dark mode` +
  `feat(ui): localised error boundaries and generated OG images`.

## On completion

Set T19 to `[R]` in `TODO.md` + a journal entry recording the built-CSS
font rule and anything the dark theme forced you to change.
