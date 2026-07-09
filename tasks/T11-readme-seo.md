# T11 — README, license and SEO polish

**Read first:** `docs/CONTEXT.md` (§1–§3, §6, §7).
**Dependencies:** T10 and T12 accepted (the CI badge and the
footer/disclaimer must be on the screenshots). **Role:** Frontend/Docs.
**Branch:** work in `main`.

## Goal

The project storefront: an English README with screenshots and a CI
badge, an MIT license, SEO details (x-default hreflang, sitemap,
robots).

## Steps

1. **README.md** (root, English, replace the current one): name and a
   one-paragraph product description; the CI badge for the T10 workflow;
   features (4-regime calculator, housing dashboard, en/et/ru i18n);
   screenshots; short architecture overview (monorepo: Next.js 15 App
   Router + FastAPI + Postgres, backend layers, 1:1 types); Getting
   started — the exact commands from CONTEXT §7 (compose, seed, uvicorn,
   npm run dev); Testing (pytest, `npm run e2e` with the backend
   precondition); Project structure (a short tree); License.
2. **Screenshots**: capture via a Playwright script (do not commit it
   into the e2e suite — a separate, manually run
   `frontend/scripts/screenshots.ts`) with the backend running: home,
   calculator with results, housing dashboard; `en` locale, 1280×800
   viewport, light theme; store as `docs/screenshots/*.png`, embed in
   the README.
3. **LICENSE** — MIT, `Copyright (c) 2026 Pavel Jevstignejev`.
4. **SEO**:
   - `x-default` in the hreflang alternates of all three pages and the
     layout (pointing at the `en` version);
   - `frontend/src/app/sitemap.ts` — all pages × locales, absolute URLs
     from the `NEXT_PUBLIC_SITE_URL` env var (default
     `http://localhost:3000`, add to `frontend/.env.example`);
   - `frontend/src/app/robots.ts` — allow all + a sitemap link;
   - OG metadata in the layout (title/description from dictionaries,
     type website).
5. Verification: `npm run build`; `curl /sitemap.xml` and `/robots.txt`;
   hreflang with x-default in every page's HTML; `npm run e2e` →
   6 passed.
6. Commits: `docs: english readme with screenshots and mit license`,
   `feat(frontend): sitemap, robots and x-default hreflang`.

## Non-goals

- Do not change page content, feature components, the backend, or CI.
- No analytics, structured data, or OG image generators.

## Acceptance criteria

- [ ] README: badge, screenshots, commands reproducible by copy-paste.
- [ ] MIT LICENSE in place.
- [ ] `/sitemap.xml` and `/robots.txt` answer 200 and are correct;
      hreflang everywhere includes `x-default` → en.
- [ ] `npm run build` clean, `npm run e2e` → 6 passed.

## On completion

Set T11 to `[R]` in `TODO.md` + a journal entry (what was verified and how).
