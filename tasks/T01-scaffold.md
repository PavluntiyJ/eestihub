# T01 — Скаффолд monorepo

**Прочитай сначала:** `docs/CONTEXT.md` (разделы 2, 3, 6).
**Зависимости:** нет. **Роль:** DevOps / Fullstack.

## Цель
Пустая папка проекта превращается в рабочий каркас monorepo: git, структура
папок, Docker Compose с Postgres, базовые конфиги фронта и бэка.

## Что сделать

1. `git init`, создать `.gitignore` (Python + Node + Next.js + .env + IDE).
2. Создать дерево папок ровно по разделу 3 CONTEXT.md (пустые пакеты Python —
   с `__init__.py`).
3. `docker-compose.yml` в корне: сервис `db` — `postgres:16-alpine`,
   порт 5432, volume для данных, healthcheck, креды через env
   (default: estihub/estihub/estihub_dev).
4. `backend/requirements.txt`: fastapi, uvicorn[standard], pydantic>=2,
   pydantic-settings, sqlalchemy>=2, psycopg[binary], pytest, httpx.
   Версии зафиксировать (pin) на актуальные стабильные.
5. `backend/.env.example`: DATABASE_URL, CORS_ORIGINS.
6. Фронтенд: `npx create-next-app@latest frontend` — TypeScript, Tailwind,
   App Router, `src/`-директория, ESLint. Затем инициализировать shadcn/ui
   (`npx shadcn@latest init`). Добавить `frontend/.env.example`
   с `NEXT_PUBLIC_API_URL=http://localhost:8000`.
7. Корневой `README.md` (на английском, кратко): что за проект, стек,
   как запустить (раздел 7 CONTEXT.md).
8. Коммит: `chore: scaffold monorepo (frontend, backend, docker-compose)`.

## Чего НЕ делать
- Не писать эндпоинты и бизнес-логику (это T02/T03).
- Не добавлять сервисы backend/frontend в docker-compose (пока только db).
- Не ставить лишних зависимостей «на будущее».

## Критерии приёмки
- [ ] `docker compose up -d db` поднимает Postgres, healthcheck зелёный.
- [ ] `cd frontend && npm run dev` открывает дефолтную страницу без ошибок.
- [ ] `pip install -r backend/requirements.txt` проходит в чистом venv (Python 3.11+).
- [ ] `git log` содержит один осмысленный коммит; `.env` файлы в `.gitignore`.

## По завершении
Обнови строку T01 в `TODO.md` на `[R]`, добавь запись в журнал
(дата · кто · что сделано · как проверено).
