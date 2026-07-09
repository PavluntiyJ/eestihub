# T07 — Header navigation to /calculator and /housing

**Read first:** `docs/CONTEXT.md` (§4, §6).
**Dependencies:** T05, T06 accepted (both pages are already in `master`).
**Role:** Frontend (TS/React). **Branch:** work in `master`.

## Goal

Both features are done but unreachable from the UI — add header
navigation to the home page, the calculator and the housing dashboard,
with active-section highlighting, in three languages.

## Steps

1. `src/components/site-nav.tsx` — a client leaf component (modeled on
   `language-switcher.tsx`): links Home (`/`), Calculator
   (`/calculator`), Rent (`/housing`) via `Link` from
   `@/i18n/navigation`; determine the active section with `usePathname`
   and mark it with styling + `aria-current="page"`. For `/` match the
   path exactly; for the others match by prefix.
2. Mount `SiteNav` in `site-header.tsx` between the brand and the
   language switcher. The header must not break on narrow screens
   (wrapping the nav onto a second row is fine; do NOT build a burger
   menu).
3. Labels — a `nav` namespace in `src/messages/{en,et,ru}.json`
   (`home`, `calculator`, `housing`), translate carefully yourself.
4. Verification: prod build (`npm run build` + `next start`), link
   clicks preserve the locale (from `/et/calculator` the "Rent" link
   goes to `/et/housing`), the active item is highlighted.
5. Commit: `feat(frontend): header navigation with active section state`.

## Non-goals

- Do not touch the backend, pages, dictionary keys outside `nav`,
  `language-switcher.tsx`, `lib/api.ts`, `types/api.ts`.
- No new dependencies, burger menus, dropdowns, or `any`.

## Acceptance criteria

- [ ] `npm run build` passes with no type or ESLint errors.
- [ ] All three locales show 3 translated header links; navigation
      preserves the current locale.
- [ ] The active section carries `aria-current="page"` (on
      `/et/housing` "Rent" is highlighted, on `/en` — "Home").
- [ ] `'use client'` — only in `site-nav.tsx` among the new code;
      `site-header.tsx` stays a Server Component.
- [ ] The header holds up at ~360px width (verify at least through
      sensible Tailwind breakpoints in the code).

## On completion

Set T07 to `[R]` in `TODO.md` + a journal entry (what was verified and how).
