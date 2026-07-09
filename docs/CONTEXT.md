# CONTEXT.md — Архитектурный контекст проекта

> Этот файл — единый источник правды для всех ИИ-исполнителей.
> Прочитай его ПОЛНОСТЬЮ перед выполнением любой задачи из `tasks/`.
> Менять этот файл может только оркестратор (Tech Lead).

## 1. Что мы строим

**EstiHub** (рабочее название) — интерактивный веб-сервис для экспатов и
предпринимателей в Эстонии. Цели: высокая производительность, SEO,
чистая архитектура (проект идёт в портфолио/CV).

MVP — две фичи:
1. **Калькулятор налогов** — сравнение net-дохода при 4 режимах:
   Tööleping (трудовой договор), Juhatuse liige (член правления),
   FIE (ИП), Ettevõtluskonto (личный бизнес-счёт LHV).
2. **Дашборд аренды жилья** — мок-данные о средних ценах аренды по
   районам Таллина, API + интерактивная визуализация.

## 2. Стек (зафиксирован, не менять)

| Слой      | Технология |
|-----------|-----------|
| Frontend  | Next.js 15 (App Router), TypeScript strict, Tailwind CSS, shadcn/ui |
| Графики   | Recharts — только через shadcn/ui chart-компоненты, клиентские листовые компоненты |
| E2E       | Playwright (`@playwright/test`, только chromium), тесты в `frontend/e2e/` |
| Backend   | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.x |
| DB        | PostgreSQL 16 (Docker) |
| Dev-среда | Docker Compose (пока только для Postgres; фронт и бэк запускаются локально) |

## 3. Структура репозитория (monorepo)

```
new_site_project/
├── frontend/                  # Next.js 15
│   └── src/
│       ├── app/               # App Router: страницы = Server Components
│       ├── components/ui/     # shadcn/ui (генерируется CLI)
│       ├── features/          # фичи: tax-calculator/, housing/
│       │   └── <feature>/     #   components/, hooks/, api.ts
│       ├── lib/               # утилиты, api-client
│       └── types/             # типы, зеркалящие Pydantic-схемы
├── backend/
│   ├── app/
│   │   ├── main.py            # создание FastAPI app, CORS, роутеры
│   │   ├── core/config.py     # настройки (pydantic-settings), env
│   │   ├── core/tax_rates.py  # налоговые ставки — ТОЛЬКО здесь
│   │   ├── api/v1/routes/     # тонкие роуты: health.py, taxes.py, housing.py
│   │   ├── schemas/           # Pydantic v2 схемы запросов/ответов
│   │   ├── services/          # бизнес-логика: tax_service.py, housing_service.py
│   │   └── models/            # SQLAlchemy модели
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── docker-compose.yml         # postgres (+ позже backend/frontend)
├── docs/CONTEXT.md            # этот файл
├── tasks/                     # брифы задач для исполнителей
├── TODO.md                    # доска задач и журнал
└── CLAUDE.md
```

## 4. Правила кода (обязательны для всех задач)

- **Никаких `any`** в TypeScript. `tsconfig` strict.
- Роуты FastAPI — тонкие: валидация + вызов сервиса. Вся математика — в `services/`.
- Server Components по умолчанию; `'use client'` только для интерактива
  (формы, графики, локальный стейт).
- TS-типы в `frontend/src/types/` должны 1:1 соответствовать Pydantic-схемам
  бэкенда (имена полей snake_case как в API).
- Код, идентификаторы, комментарии, коммиты — **на английском**
  (проект для портфолио). Комментировать только неочевидные архитектурные решения.
- Налоговые ставки/константы — только в `backend/app/core/tax_rates.py`,
  никаких магических чисел в сервисах.
- Каждый эндпоинт под префиксом `/api/v1/`.

## 5. Контракт API (v1)

### GET /api/v1/health
Ответ `200`: `{ "status": "ok" }`

### POST /api/v1/calculate-taxes
Запрос:
```json
{
  "gross_monthly_income": 3000.0,
  "pension_pillar_rate": 0.02
}
```
- `gross_monthly_income`: float > 0 — брутто-доход в месяц, EUR.
- `pension_pillar_rate`: 0.0 | 0.02 | 0.04 | 0.06 (II ступень пенсии; default 0.02).

Ответ `200` — сравнение по всем 4 режимам:
```json
{
  "input": { "gross_monthly_income": 3000.0, "pension_pillar_rate": 0.02 },
  "results": [
    {
      "regime": "tooleping",
      "label": "Employment contract (Tööleping)",
      "employer_total_cost": 4014.0,
      "gross_income": 3000.0,
      "breakdown": [
        { "name": "income_tax", "amount": 462.0 },
        { "name": "unemployment_insurance_employee", "amount": 48.0 },
        { "name": "pension_pillar_ii", "amount": 60.0 }
      ],
      "net_income": 2430.0,
      "effective_tax_rate": 0.395
    }
  ]
}
```
- `regime`: `"tooleping" | "juhatuse_liige" | "fie" | "ettevotluskonto"`.
- `effective_tax_rate` = 1 − net_income / employer_total_cost.
- Числа в примере иллюстративные, точность расчёта — 2 знака (Decimal, округление банковское не нужно — стандартный ROUND_HALF_UP).

### Налоговая логика (Эстония, 2026 — ставки ПРОВЕРИТЬ на emta.ee перед реализацией)
Предполагаемые значения для `tax_rates.py` (исполнитель задачи T03 обязан
сверить с актуальными данными и записать источник в комментарий):
- Подоходный налог: 22%.
- Необлагаемый минимум: 700 €/мес (универсальный с 2026).
- Социальный налог: 33% (платит работодатель; для FIE — сам FIE).
- Страхование от безработицы: 1.6% работник + 0.8% работодатель (только tööleping).
- II пенсионная ступень: 2/4/6% (tööleping; для juhatuse liige — не применяется по умолчанию).
- Juhatuse liige: 22% подоходный + 33% соцналог, БЕЗ страхования от безработицы.
- FIE: соцналог 33% с чистого дохода (упрощённо, без потолка в MVP), затем подоходный 22%.
- Ettevõtluskonto (проверено оркестратором по emta.ee 2026-07-09):
  ставка 40% ОТМЕНЕНА с 01.01.2025. Базовая ставка — 20% с поступлений;
  для участников II пенсионной ступени ставка выше: 22% / 24% / 26%
  при взносе 2% / 4% / 6% соответственно (т.е. 20% + pension_pillar_rate).
  При поступлениях свыше 40 000 €/год физлицо обязано зарегистрироваться
  предпринимателем (для MVP — только справочный факт, в расчёте не участвует).
  Других налогов нет.

### GET /api/v1/housing/rents  (фича 2, задача T05)
Ответ: список районов Таллина с мок-данными:
```json
{
  "city": "Tallinn",
  "updated_at": "2026-07-01",
  "districts": [
    { "name": "Kesklinn", "avg_rent_1room": 550, "avg_rent_2room": 750,
      "avg_rent_3room": 950, "avg_utilities": 180, "lat": 59.437, "lon": 24.745 }
  ]
}
```

## 6. Интернационализация (i18n) — обязательное требование

Сайт триязычный: **английский (en, default), эстонский (et), русский (ru)**.

- Библиотека: **next-intl** (App Router-нативная, SSR/SEO-совместимая).
- Роутинг с локалью в пути: `/{locale}/...` → структура `src/app/[locale]/...`;
  middleware next-intl для редиректа `/` → `/en` и определения локали.
- Словари: `frontend/src/messages/{en,et,ru}.json`. Никаких захардкоженных
  пользовательских строк в компонентах — только ключи переводов.
- SEO: `hreflang`-альтернативы в metadata, `lang` в `<html>` по локали.
- Переключатель языка — в header (клиентский листовой компонент).
- API бэкенда локале-нейтрален: возвращает машинные ключи/числа
  (`regime: "tooleping"`), человекочитаемые подписи (`label`) фронтенд берёт
  из словарей. Поле `label` в ответе API — служебное/отладочное, для UI не использовать.

## 7. Локальный запуск (после T01–T02)

```bash
docker compose up -d db                      # Postgres на :5432
cd backend && python -m scripts.seed_housing # сид housing-данных (после T08)
cd backend && uvicorn app.main:app --reload  # API на :8000
cd frontend && npm run dev                   # UI на :3000
cd frontend && npm run e2e                   # e2e-смоки (нужен API на :8000; после T09)
```
CORS: бэкенд разрешает `http://localhost:3000`.
Фронтенд ходит на бэкенд через `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
Бэкенд ходит в Postgres через `DATABASE_URL` (default — compose-БД, см. `backend/.env.example`).
