# T04 — Базовая страница Next.js с fetch к бэкенду

**Прочитай сначала:** `docs/CONTEXT.md` (разделы 3, 4, 5, 6 (i18n!), 7).
**Зависимости:** T02 принята (нужен работающий /api/v1/health). **Роль:** Frontend (TS/React).

## Цель
Главная страница Next.js, которая серверным fetch-ом опрашивает бэкенд
и показывает его статус. Заложить структуру `lib/api-client`, `types/`
и i18n (en/et/ru), на которую лягут фичи.

## Что сделать

0. **i18n-каркас (next-intl)** по CONTEXT.md §6: структура
   `src/app/[locale]/`, middleware (default `en`, поддержка `et`, `ru`),
   словари `src/messages/{en,et,ru}.json`, переключатель языка в header
   (клиентский листовой компонент), `lang` на `<html>` и hreflang в metadata.
   Все строки главной страницы — через словари; переводы et/ru сделать
   самостоятельно (короткие маркетинговые строки, аккуратный перевод).
1. `src/lib/api.ts`: маленький типизированный API-клиент поверх `fetch` —
   базовый URL из `process.env.NEXT_PUBLIC_API_URL`, обработка не-2xx
   (кидать типизированную ошибку), JSON-парсинг. Без axios и лишних обёрток.
2. `src/types/api.ts`: типы, зеркалящие Pydantic-схемы бэкенда:
   `HealthResponse`, а также заранее `TaxCalculationRequest/Response/
   RegimeResult/TaxLine` по контракту CONTEXT.md §5 (snake_case полей сохранить).
3. Главная страница `src/app/page.tsx` — **Server Component**:
   - hero-блок сервиса (название, один абзац о продукте, на английском);
   - статус бэкенда: серверный fetch `GET /api/v1/health`
     (`cache: 'no-store'`), бейдж online/offline через компонент shadcn/ui
     (badge/card). Бэкенд лежит → страница не падает, показывает offline.
4. Базовый layout: `layout.tsx` с метаданными (title, description для SEO),
   шрифт через `next/font`.
5. Убедиться, что `'use client'` нигде не появился без необходимости.
6. Коммит: `feat(frontend): base page with typed api client and backend status`.

## Чего НЕ делать
- Не строить UI калькулятора и дашборда (T05/T06).
- Никаких `any`, никаких сторонних HTTP-библиотек.

## Критерии приёмки
- [ ] `npm run build` проходит без ошибок типов и ESLint.
- [ ] При работающем бэкенде страница показывает статус online, при
      выключенном — offline (проверить оба случая).
- [ ] `page.tsx` — Server Component (нет `'use client'`).
- [ ] Типы в `types/api.ts` совпадают с контрактом §5 по именам полей.
- [ ] `/en`, `/et`, `/ru` открываются с переведённым контентом; `/`
      редиректит на `/en`; переключатель языка работает; в HTML корректный
      `lang` и hreflang-альтернативы.

## По завершении
Обнови T04 в `TODO.md` на `[R]` + запись в журнал (что проверено и как).
