# T10 — CI on GitHub Actions

**Read first:** `docs/CONTEXT.md` (§2, §7).
**Dependencies:** T09 accepted. **Role:** DevOps/Full-stack.
**Branch:** work in `main` (repository: github.com/PavluntiyJ/eestihub).
T12 (frontend) runs in parallel — `.github/` does not overlap with it.

## Goal

Every push/PR to `main` automatically runs backend tests, the frontend
build and the e2e suite. A green run becomes a mandatory acceptance
condition for all future tasks.

## Steps

1. `.github/workflows/ci.yml`, triggers: `push` to `main`,
   `pull_request` to `main`. Three jobs:
   - **backend**: Python 3.12, pip cache, `pip install -r
     backend/requirements.txt`, `pytest` from `backend/` (no Postgres
     needed — tests run on SQLite).
   - **frontend**: Node 22, npm cache, `npm ci`, `npm run build` from
     `frontend/`.
   - **e2e** (after the first two, via `needs`): a
     `postgres:16-alpine` service container (credentials as in
     docker-compose, healthcheck); install backend dependencies, run the
     seed (`python -m scripts.seed_housing` with `DATABASE_URL` pointing
     at the service), start `uvicorn` in the background, wait for
     `/api/v1/health`; `npm ci` + `npx playwright install --with-deps
     chromium` + `npm run e2e`. On failure upload the playwright report
     as an artifact (`actions/upload-artifact`, `if: failure()`).
2. Pin action versions to majors (`actions/checkout@v4`,
   `actions/setup-python@v5`, `actions/setup-node@v4`).
3. Verify locally everything that can be verified without GitHub: the
   yaml is valid, each job's commands run by hand on the same versions.
4. Commit: `ci: github actions for backend tests, frontend build and e2e`.
   Do NOT push — the orchestrator pushes and verifies the live run
   during review.

## Non-goals

- Do not change application code, tests, or project dependencies.
- No deploy steps, secrets, or a README badge (README is T11).
- No other workflows (release, dependabot, etc.).

## Acceptance criteria

- [ ] A single `.github/workflows/ci.yml`, triggered on push/PR to `main`.
- [ ] The backend job is green without Postgres; the e2e job uses a
      Postgres service, the seed and a real 6-test chromium run.
- [ ] The GitHub run is fully green (the orchestrator verifies after
      pushing).
- [ ] Action versions pinned; the e2e report is preserved on failure.

## On completion

Set T10 to `[R]` in `TODO.md` + a journal entry (what was verified and how).
