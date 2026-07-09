# T08 — Housing из Postgres (SQLAlchemy + сид)

**Прочитай сначала:** `docs/CONTEXT.md` (§2, §3, §5 — контракт
`GET /api/v1/housing/rents`, §7).
**Зависимости:** T05 принята. **Роль:** Backend (Python).
**Ветка:** работай в `master` (параллельно в ветке `feat/t09-e2e` идёт
T09 — frontend-тесты; backend-файлы не пересекаются).

## Цель

Заявленный в стеке Postgres начинает работать: данные аренды переезжают
из хардкода в БД. Модель SQLAlchemy, идемпотентный сид из текущих моков,
сервис читает из БД. **Контракт API v1 не меняется** — фронтенд не в
курсе перемен, кроме одного уточнения: `updated_at` становится настоящей
датой (сериализация в ту же строку `YYYY-MM-DD`).

Postgres поднимается через `docker compose up -d db` (в среде podman,
алиас `docker` работает; параметры подключения — в `.env.example`).

## Что сделать

1. Зависимости в `requirements.txt`: `sqlalchemy` 2.x и `psycopg[binary]`
   (запинить версии, как принято в файле).
2. `app/core/config.py`: настройка `database_url` (из env `DATABASE_URL`,
   дефолт — локальный Postgres из docker-compose). Обнови `.env.example`.
3. `app/core/db.py`: engine + `session factory` (синхронные — для MVP
   достаточно), FastAPI-dependency `get_session`.
4. `app/models/housing.py`: модель `DistrictRent` (таблица
   `district_rents`): `id` PK, `name` уникальный, четыре ценовых поля
   int, `lat`/`lon` float, `updated_at` date. `Base` — в `app/models/`.
5. Сид `backend/scripts/seed_housing.py`: создаёт таблицы
   (`Base.metadata.create_all` — Alembic в MVP не заводим, это решение
   оркестратора) и **идемпотентно** (upsert по `name`) заливает данные из
   `app/services/housing_data.py` — модуль моков остаётся источником
   сида. Запуск: `python -m scripts.seed_housing` из `backend/`.
6. `app/services/housing_service.py`: читает районы из БД (сортировка по
   `name`), `updated_at` ответа = max по строкам. Схема
   `HousingRentsResponse.updated_at` → `datetime.date`.
7. Роут: при недоступной БД — HTTP 503 (`Service Unavailable`), без
   стектрейса в ответе. Фронтенд уже показывает unavailable-состояние на
   любой не-2xx/сетевой ошибке — его не трогаем.
8. Тесты: без живого Postgres (SQLite in-memory через override
   `get_session`; учти отличия типов — модель должна быть совместима):
   форма ответа, 8 районов после сида тестовой сессии, 503 при
   недоступной БД. Плюс живая проверка вручную: compose-Postgres, сид,
   `curl` — результат идентичен прежнему мок-ответу (кроме типа даты).
9. Коммит: `feat(backend): serve housing rents from postgres`.

## Чего НЕ делать

- Не менять контракт §5, роуты v1, налоговый код, frontend (совсем).
- Не заводить Alembic, async-движок, пулы, ORM-модели для налогов.
- Не удалять `housing_data.py` — он теперь источник сида.

## Критерии приёмки

- [ ] `pytest` зелёный без запущенного Postgres.
- [ ] Живой прогон: `docker compose up -d db` → сид → `curl
      /api/v1/housing/rents` → 200, 8 районов, значения совпадают с
      прежними моками, `updated_at: "2026-07-01"`.
- [ ] Повторный запуск сида не дублирует строки (идемпотентность).
- [ ] БД остановлена → эндпоинт отвечает 503 (не 500 со стектрейсом);
      `/api/v1/health` и калькулятор работают без БД как раньше.
- [ ] Никаких изменений в `frontend/`.

## По завершении

Обнови T08 в `TODO.md` на `[R]` + запись в журнал (что проверено и как).
