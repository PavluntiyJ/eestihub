# T05 — Housing API (мок-данные) + дашборд аренды

**Прочитай сначала:** `docs/CONTEXT.md` (§3, §4, §5 — контракт
`GET /api/v1/housing/rents`, §6 i18n, §7).
**Зависимости:** T03, T04 приняты. **Роль:** Full-stack.
**Ветка:** работай прямо в `master` (параллельно в отдельной ветке идёт
T06 — не трогай его файлы, см. «Чего НЕ делать»).

## Цель

Полный вертикальный срез второй фичи: бэкенд отдаёт мок-данные по аренде
в районах Таллина по контракту §5, фронтенд показывает дашборд
(таблица + bar chart) на `/[locale]/housing` в трёх языках.

## Что сделать — backend

1. `app/services/housing_data.py` — мок-данные отдельным Python-модулем
   (решение оркестратора: модуль, не JSON — типизировано, без IO, при
   замене на реальный парсер меняется только этот модуль). 8 районов:
   Kesklinn, Põhja-Tallinn, Kristiine, Mustamäe, Lasnamäe, Haabersti,
   Nõmme, Pirita. Поля по контракту §5 (`name`, `avg_rent_1room`,
   `avg_rent_2room`, `avg_rent_3room`, `avg_utilities`, `lat`, `lon`).
   Значения — правдоподобные для 2026 (Kesklinn дороже, Lasnamäe дешевле);
   в комментарии модуля явно пометь, что это mock, и дату.
2. `app/schemas/housing.py` — Pydantic v2: `DistrictRent`,
   `HousingRentsResponse` (`city`, `updated_at` ISO-дата строкой,
   `districts`).
3. `app/services/housing_service.py` — сервис, собирающий ответ из
   `housing_data`. Роут математики/данных не содержит.
4. `app/api/v1/routes/housing.py` — тонкий `GET /api/v1/housing/rents`,
   подключить в v1-router.
5. Тесты (`backend/tests/`): статус 200, форма ответа соответствует
   схеме, ровно 8 районов, все поля присутствуют, цены > 0,
   `avg_rent_1room < avg_rent_3room` для каждого района.

## Что сделать — frontend

6. `src/types/api.ts` — добавить `DistrictRent`, `HousingRentsResponse`
   (snake_case, 1:1 со схемами). Существующие типы не менять.
7. `src/lib/api.ts` — добавить `getHousingRents()`; существующий код не
   переформатировать.
8. Зависимость графиков: `recharts` через shadcn/ui chart-компонент
   (`npx shadcn@latest add chart`). Решение оркестратора: Recharts —
   стандарт для shadcn/ui. Других новых зависимостей не добавлять.
9. Страница `src/app/[locale]/housing/page.tsx` — **Server Component**:
   серверный fetch (`cache: 'no-store'`), при недоступном бэкенде —
   аккуратное состояние «данные недоступны» (страница не падает).
   Компоненты фичи — в `src/features/housing/components/`:
   - таблица районов (shadcn table): все колонки контракта, без lat/lon;
   - bar chart средних цен по районам (`avg_rent_2room`) — клиентский
     листовой компонент (`'use client'` только в нём).
10. i18n: namespace `housing` в `src/messages/{en,et,ru}.json` — заголовок
    страницы, подписи колонок, состояния. Названия районов — имена
    собственные, не переводятся. Метаданные страницы
    (`generateMetadata`): локализованные title/description + hreflang
    (по образцу layout).
11. Коммиты (2, conventional): `feat(backend): housing rents mock api`,
    затем `feat(frontend): tallinn rent dashboard`.

## Чего НЕ делать

- Не трогать: `site-header.tsx`, страницу калькулятора и
  `src/features/tax-calculator/` (параллельная T06), существующие ключи
  словарей, налоговый код backend.
- Не добавлять навигационные ссылки в header (будет отдельная T07).
- Никаких `any`, никаких БД/SQLAlchemy — данные мок, Postgres не нужен.

## Критерии приёмки

- [ ] `pytest` зелёный (включая новые тесты housing).
- [ ] `curl localhost:8000/api/v1/housing/rents` → 200, 8 районов, форма §5.
- [ ] `npm run build` проходит без ошибок типов и ESLint.
- [ ] `/en/housing`, `/et/housing`, `/ru/housing` открываются с
      переведёнными строками; таблица и bar chart отображают 8 районов.
- [ ] Бэкенд выключен → страница housing показывает состояние
      «недоступно», не 500.
- [ ] `'use client'` — только в chart-компоненте (и ранее принятом
      language-switcher).
- [ ] Типы в `types/api.ts` совпадают со схемами backend по именам полей.

## По завершении

Обнови T05 в `TODO.md` на `[R]` + запись в журнал (что проверено и как).
