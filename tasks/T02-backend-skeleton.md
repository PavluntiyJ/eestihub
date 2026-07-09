# T02 — Скелет FastAPI + health-эндпоинт

**Прочитай сначала:** `docs/CONTEXT.md` (разделы 3, 4, 5, 6).
**Зависимости:** T01 принята. **Роль:** Backend (Python).

## Цель
Работающее FastAPI-приложение с чистой модульной структурой и первым
эндпоинтом `GET /api/v1/health`.

## Что сделать

1. `app/core/config.py`: класс `Settings` на pydantic-settings
   (DATABASE_URL, CORS_ORIGINS), кешированный `get_settings()`.
2. `app/main.py`: фабрика `create_app()` — создаёт FastAPI
   (title, version), вешает CORSMiddleware (origins из настроек),
   подключает роутер v1 с префиксом `/api/v1`.
3. `app/api/v1/routes/health.py`: `GET /health` → `{"status": "ok"}`,
   схема ответа — Pydantic-модель в `app/schemas/health.py`.
4. Агрегирующий роутер `app/api/v1/__init__.py` (или `router.py`),
   куда подключаются все роуты v1.
5. Тест `tests/test_health.py` через `httpx` + `fastapi.testclient`:
   статус 200 и тело `{"status": "ok"}`.
6. Коммит: `feat(backend): fastapi skeleton with health endpoint`.

## Чего НЕ делать
- Не подключать SQLAlchemy к реальной БД (модели/сессии — позже, когда понадобятся).
- Не реализовывать налоговую логику (T03).

## Критерии приёмки
- [ ] `uvicorn app.main:app --reload` из `backend/` стартует без ошибок.
- [ ] `curl localhost:8000/api/v1/health` → `{"status":"ok"}`.
- [ ] `/docs` (Swagger) открывается и показывает эндпоинт.
- [ ] `pytest` из `backend/` — зелёный.
- [ ] Роут тонкий, структура папок соответствует CONTEXT.md §3.

## По завершении
Обнови T02 в `TODO.md` на `[R]` + запись в журнал с выводом `pytest`.
