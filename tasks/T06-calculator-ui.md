# T06 — UI калькулятора налогов (форма + сравнение режимов)

**Прочитай сначала:** `docs/CONTEXT.md` (§4, §5 — контракт
`POST /api/v1/calculate-taxes`, §6 i18n, §7).
**Зависимости:** T03, T04 приняты. **Роль:** Frontend (TS/React).
**Ветка:** `feat/t06-calculator-ui` от текущего `master`. Параллельно в
`master` идёт T05 (housing). Перед сдачей в `[R]` сделай
`git rebase master`; конфликтов быть не должно, если соблюдён раздел
«Чего НЕ делать».

## Цель

Страница `/[locale]/calculator`: форма ввода дохода → POST к бэкенду →
наглядное сравнение net-дохода по 4 налоговым режимам Эстонии, в трёх
языках. Backend-контракт готов (T03) и не меняется.

## Что сделать

1. `src/lib/api.ts` — добавить `calculateTaxes(request)`
   (POST, JSON body, `Content-Type: application/json`) поверх
   существующего `fetchJson`. Существующий код не переформатировать.
   Типы брать из `src/types/api.ts` — они уже есть, файл НЕ менять.
2. Страница `src/app/[locale]/calculator/page.tsx` — **Server Component**:
   заголовок/описание из словарей, локализованные `generateMetadata`
   (title/description + hreflang по образцу layout). Внутри — клиентская
   форма.
3. `src/features/tax-calculator/components/` — компоненты фичи:
   - `calculator-form.tsx` (`'use client'`): поле
     `gross_monthly_income` (number, EUR, > 0), select
     `pension_pillar_rate` (0% / 2% / 4% / 6%, default 2%), submit.
     Состояния: загрузка, ошибка API (`ApiError` → человекочитаемое
     сообщение из словаря), невалидный ввод → submit заблокирован.
   - результаты: 4 карточки режимов (shadcn card), отсортированы по
     `net_income` убыванию: net-доход, полная стоимость для работодателя
     (`employer_total_cost`), эффективная ставка
     (`effective_tax_rate`), раскрытый breakdown построчно.
   - сравнительная инфографика: горизонтальные полосы net-дохода
     (лучший режим = 100% ширины), чистый Tailwind — **без библиотек
     графиков и вообще без новых npm-зависимостей** (recharts ставит
     параллельная T05, не дублируй).
4. Локализация (namespace `calculator` в `src/messages/{en,et,ru}.json`):
   - названия режимов — из словарей по ключу `regime`
     (`tooleping`, `juhatuse_liige`, `fie`, `ettevotluskonto`);
     поле `label` из API в UI НЕ использовать (CONTEXT §6);
   - названия строк breakdown — из словарей по ключу `name`; полный
     список ключей, которые сейчас отдаёт бэкенд: `income_tax`,
     `unemployment_insurance_employee`, `pension_pillar_ii`,
     `social_tax`, `business_income_tax` (сверь с
     `backend/app/services/tax_service.py` перед сдачей);
   - деньги и проценты форматировать через `Intl.NumberFormat` текущей
     локали (EUR, 2 знака; проценты из долей вида 0.395).
5. Проверка вручную: с бэкендом (uvicorn из `backend/`, venv) ввод
   3000 € / 2% → 4 карточки, Tööleping net **2409.76**; без бэкенда →
   сообщение об ошибке, страница не падает.
6. Коммит: `feat(frontend): tax calculator ui with regime comparison`.

## Чего НЕ делать

- Не трогать: backend полностью, `src/types/api.ts`,
  `site-header.tsx`, существующие ключи словарей, `src/app/[locale]/page.tsx`,
  `src/features/housing/` (параллельная T05).
- Не добавлять навигационные ссылки в header (будет отдельная T07).
- Никаких новых npm-зависимостей, никаких `any`, никаких захардкоженных
  UI-строк.

## Критерии приёмки

- [ ] `npm run build` проходит без ошибок типов и ESLint.
- [ ] `/en/calculator`, `/et/calculator`, `/ru/calculator` — форма и
      результаты полностью переведены (режимы, breakdown, ошибки).
- [ ] Расчёт 3000 € / 2% совпадает с API (Tööleping net 2409.76),
      карточки отсортированы по net-доходу.
- [ ] Ошибка сети/бэкенда → понятное сообщение, без падения страницы.
- [ ] `page.tsx` — Server Component; `'use client'` только в листовых
      компонентах фичи.
- [ ] `label` из ответа API нигде не рендерится.
- [ ] Деньги/проценты отформатированы по локали (`Intl.NumberFormat`).
- [ ] Ветка перебазирована на актуальный `master`, конфликтов нет.

## По завершении

Обнови T06 в `TODO.md` на `[R]` + запись в журнал (что проверено и как);
ветку не мержить — мерж делает оркестратор после ревью.
