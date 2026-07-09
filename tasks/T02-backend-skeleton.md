# T02 — FastAPI skeleton + health endpoint

**Read first:** `docs/CONTEXT.md` (sections 3, 4, 5, 6).
**Dependencies:** T01 accepted. **Role:** Backend (Python).

## Goal
A working FastAPI application with a clean modular structure and the
first endpoint, `GET /api/v1/health`.

## Steps

1. `app/core/config.py`: `Settings` class on pydantic-settings
   (DATABASE_URL, CORS_ORIGINS), cached `get_settings()`.
2. `app/main.py`: `create_app()` factory — creates FastAPI (title,
   version), attaches CORSMiddleware (origins from settings), mounts the
   v1 router under the `/api/v1` prefix.
3. `app/api/v1/routes/health.py`: `GET /health` → `{"status": "ok"}`,
   response schema — a Pydantic model in `app/schemas/health.py`.
4. Aggregating router in `app/api/v1/__init__.py` (or `router.py`) that
   collects all v1 routes.
5. Test `tests/test_health.py` via `httpx` + `fastapi.testclient`:
   status 200 and body `{"status": "ok"}`.
6. Commit: `feat(backend): fastapi skeleton with health endpoint`.

## Non-goals
- Do not wire SQLAlchemy to a real DB (models/sessions come later).
- Do not implement tax logic (T03).

## Acceptance criteria
- [ ] `uvicorn app.main:app --reload` from `backend/` starts cleanly.
- [ ] `curl localhost:8000/api/v1/health` → `{"status":"ok"}`.
- [ ] `/docs` (Swagger) opens and shows the endpoint.
- [ ] `pytest` from `backend/` is green.
- [ ] The route is thin; folder structure matches CONTEXT.md §3.

## On completion
Set T02 to `[R]` in `TODO.md` + journal entry with the `pytest` output.
