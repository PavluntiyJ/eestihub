# TODO — доска задач EstiHub

Статусы: `[ ]` не начата · `[>]` в работе · `[R]` на ревью у оркестратора · `[x]` принята

Правила для исполнителей:
1. Перед началом прочитай `docs/CONTEXT.md` и файл своей задачи в `tasks/`.
2. Взял задачу — поставь `[>]` и впиши исполнителя. Закончил — `[R]` + запись в журнал.
3. Статус `[x]` ставит только оркестратор после ревью.
4. Не выходи за рамки задачи. Заметил проблему вне скоупа — запиши в «Заметки для оркестратора», не чини сам.

## Итерация 1 — каркас MVP

| # | Задача | Файл брифа | Статус | Исполнитель | Зависит от |
|---|--------|-----------|--------|-------------|------------|
| T01 | Скаффолд monorepo: git, папки, docker-compose, конфиги | tasks/T01-scaffold.md | `[x]` | gpt-5.5 | — |
| T02 | Скелет FastAPI + GET /api/v1/health | tasks/T02-backend-skeleton.md | `[x]` | gpt-5.5-codex | T01 |
| T03 | Сервис расчёта налогов + POST /api/v1/calculate-taxes + тесты | tasks/T03-tax-calculator.md | `[R]` | gpt-5.5-codex | T02 |
| T04 | Базовая страница Next.js с fetch к бэкенду | tasks/T04-frontend-base.md | `[ ]` | — | T02 |

## Итерация 2 — фичи (не начинать без команды оркестратора)

| # | Задача | Файл брифа | Статус | Исполнитель | Зависит от |
|---|--------|-----------|--------|-------------|------------|
| T05 | Housing API (мок-данные) + дашборд аренды | tasks/T05-housing-dashboard.md | `[ ]` | — | T03, T04 |
| T06 | UI калькулятора налогов (форма + инфографика) | брифа ещё нет | `[ ]` | — | T03, T04 |

## Журнал (новые записи сверху)

- 2026-07-09 · gpt-5.5-codex · Выполнен T03: сверены ставки EMTA 2026, добавлены `tax_rates.py` с источниками, Pydantic-схемы, сервис сравнения 4 режимов, тонкий `POST /api/v1/calculate-taxes`, тесты с ручными выкладками · Проверено: `pytest` → 13 passed; `curl -X POST localhost:8000/api/v1/calculate-taxes` с примером из CONTEXT.md → 4 результата, Tööleping net 2409.76, employer_total_cost 4014.00.
- 2026-07-09 · оркестратор · Ревью T02: принята `[x]`. Проверено независимо в чистом venv: pytest 1 passed; uvicorn стартует; `GET /api/v1/health` → 200 `{"status":"ok"}`; `/docs` → 200; CORS-заголовки для localhost:3000 корректны. Код: фабрика create_app, кешированные настройки, тонкий роут, Literal-схема — соответствует правилам. Не блокер: starlette предупреждает о deprecation httpx в testclient (upstream, следить при обновлениях). НАЗНАЧЕНИЕ: T03 (tasks/T03-tax-calculator.md) → gpt-5.5-codex; после сдачи T03 — сразу T04, не дожидаясь ревью (T04 от T03 не зависит).
- 2026-07-09 · gpt-5.5-codex · Выполнен T02: добавлены FastAPI `create_app()`, pydantic-settings конфиг, CORS, v1 router, `GET /api/v1/health`, Pydantic-схема и тест · Проверено: `uvicorn app.main:app --reload` стартует, `curl localhost:8000/api/v1/health` → `{ "status": "ok" }`, `/docs` → 200 и OpenAPI содержит `/api/v1/health`, `pytest` → 1 passed.
- 2026-07-09 · оркестратор · Решение владельца: все задачи выполняет GPT 5.5 Codex (раскладка DeepSeek/Grok отменена). T02 в работе у gpt-5.5-codex.
- 2026-07-09 · оркестратор · НАЗНАЧЕНИЕ: T02 (tasks/T02-backend-skeleton.md) → deepseek-pro-v4. Зависимость T01 закрыта. Дополнительно: включить в коммит T02 незакоммиченную правку docker-compose.yml (полное имя образа) отдельным коммитом `fix: use fully qualified postgres image name for podman compatibility`.
- 2026-07-09 · оркестратор · Среда: установлены podman 5.8.4 + podman-compose + podman-docker (алиас `docker` работает). В docker-compose.yml образ заменён на полное имя `docker.io/library/postgres:16-alpine` (podman не резолвит короткие имена). `docker compose up -d db` → контейнер healthy, `psql` внутри отвечает (PostgreSQL 16.14). Отложенный критерий T01 закрыт полностью.
- 2026-07-09 · оркестратор · Ревью T01: принята `[x]`. Проверено: git-история чистая (1 conventional-коммит, артефакты/.env не закоммичены), структура по CONTEXT.md §3, compose с healthcheck и env-дефолтами, версии запинены, README ок. Docker/Podman в среде нет вовсе — статическая проверка compose пройдена, живой запуск Postgres отложен до задач с БД (итерация 2); до этого установить docker или podman-compose. Дальше: T02 → DeepSeek Pro v4.
- 2026-07-09 · gpt-5.5 · Выполнен T01: git init, структура monorepo, Docker Compose для Postgres, backend requirements/env, frontend Next.js 15 + shadcn/ui, README · Проверено: `npm run dev` → `GET / 200`, `pip install -r backend/requirements.txt` в чистом venv → OK, `git log` после коммита; `docker compose up -d db` не выполнен из-за отсутствия `docker` в среде.
- 2026-07-09 · оркестратор · Добавлен AGENTS.md — правила для opencode-исполнителей; распределение моделей: T01/T03 → GPT 5.5, T02 → DeepSeek Pro v4, T04 → Grok 4.5 (пробное, по итогам скорректируем).
- 2026-07-09 · оркестратор · Добавлено требование триязычности (en/et/ru): CONTEXT.md §6, обновлены брифы T04/T05.
- 2026-07-09 · оркестратор · Создан каркас оркестрации: CONTEXT.md, TODO.md, брифы T01–T05.

## Заметки для оркестратора

_(исполнители пишут сюда вопросы и найденные проблемы вне скоупа)_

- 2026-07-09 · gpt-5.5-codex · При сверке T03 найдено расхождение с прежним предположением CONTEXT.md/T03 по ettevõtluskonto: EMTA Entrepreneur account page (проверено 2026-07-09) указывает, что ставка 40% больше не применяется с 01.01.2025; ставка business income tax в 2026 — 20%, а регистрационный порог — 40 000 €/год. В реализации использована актуальная ставка EMTA 20%.

- 2026-07-09 · gpt-5.5 · В текущей среде отсутствует команда `docker`, поэтому критерий `docker compose up -d db` и healthcheck Postgres не удалось проверить локально.
  - ↳ оркестратор: подтверждаю, Docker/Podman на хосте нет — не вина исполнителя. Compose проверен статически, живой запуск отложен до первой задачи с БД. РЕШЕНО.
