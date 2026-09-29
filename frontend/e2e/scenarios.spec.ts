import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import {
  encodeScenario,
  decodeScenario,
  parseScenario,
  STORAGE_KEY,
  type Scenario,
} from "../src/features/scenarios/serializer";
import en from "../src/messages/en.json";
import et from "../src/messages/et.json";
import ru from "../src/messages/ru.json";
import { THEME_STORAGE_KEY } from '../src/lib/theme';

const scenario: Scenario = {
  version: 1,
  currency: "EUR",
  saved_at: "2026-09-29T12:00:00Z",
  budget: {
    income: {
      kind: "employment",
      gross_monthly_income: 3000,
      pension_pillar_rate: 0.02,
    },
    monthly_non_housing: 700,
    monthly_savings: 300,
    housing_share: 0.35,
    apartment: null,
  },
  candidates: [
    {
      id: "a",
      name: "My private apartment",
      address: "Mustamäe tee 5",
      costs: {
        rent: 650,
        utilities: { summer: 100, winter: 200, basis: "user_bill" },
        move_in: { first_rent: 650, deposit: 650, broker_fee: 0, setup: 0 },
      },
    },
    {
      id: "b",
      name: "Unknown bills",
      address: null,
      costs: {
        rent: 500,
        utilities: { summer: null, winter: null, basis: "unknown" },
        move_in: null,
      },
    },
  ],
};
async function importPlan(page: Page, locale = "en") {
  await page.goto(`/${locale}/compare#plan=${encodeScenario(scenario)}`);
  await expect(page.getByTestId("scenario-review")).toBeVisible();
  const messages = { en, et, ru }[locale as "en" | "et" | "ru"];
  await page
    .getByRole("button", { name: messages.scenarios.apply, exact: true })
    .click();
  await expect(page.getByTestId("comparison-result")).toHaveCount(2);
}

test('dictionary keys match for every locale',()=>{
  function flatten(value:object,prefix=''):string[]{return Object.entries(value).flatMap(([key,child])=>typeof child==='object'&&child!==null?flatten(child,`${prefix}${key}.`):[`${prefix}${key}`]).sort();}
  expect(flatten(et)).toEqual(flatten(en));expect(flatten(ru)).toEqual(flatten(en));
});

test('JSON import requires review, export contains inputs only',async({page})=>{
  await page.goto('/en/compare');
  await page.getByLabel(en.scenarios.import,{exact:true}).setInputFiles({name:'plan.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(scenario))});
  await expect(page.getByTestId('scenario-review')).toBeVisible();
  await expect(page.getByTestId('comparison-card')).toHaveCount(0);
  await page.getByRole('button',{name:en.scenarios.apply,exact:true}).click();
  await expect(page.getByTestId('comparison-result')).toHaveCount(2);
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:en.scenarios.export,exact:true}).click();
  const file=await download;const stream=await file.createReadStream();let text='';for await(const chunk of stream!)text+=chunk.toString();
  const exported=parseScenario(text);expect(exported.candidates).toEqual(scenario.candidates);expect(text).not.toContain('housing_allowance');
});

test('changing a budget invalidates comparisons while preserving the shortlist',async({page})=>{
  await importPlan(page);
  await page.getByRole('link',{name:en.compare.editBudget,exact:true}).click();
  await page.locator('#planner-gross-income').fill('1000');
  await page.getByRole('link',{name:en.nav.compare,exact:true}).click();
  await expect(page.getByTestId('comparison-card')).toHaveCount(2);
  await expect(page.getByTestId('comparison-result')).toHaveCount(0);
  await expect(page.getByRole('button',{name:en.scenarios.save,exact:true})).toBeDisabled();
});

test('candidate edit draft survives locale navigation',async({page})=>{
  await page.goto('/en/compare');await page.getByRole('button',{name:en.compare.add}).click();
  await page.getByLabel(en.compare.name,{exact:true}).fill('Work in progress');
  await page.getByLabel(en.apartment.fields.rent,{exact:true}).fill('650');
  await page.getByRole('link',{name:'ET',exact:true}).click();
  await expect(page.getByLabel(et.compare.name,{exact:true})).toHaveValue('Work in progress');
  await expect(page.getByLabel(et.apartment.fields.rent,{exact:true})).toHaveValue('650');
});

test('explore remains accessible in dark mode with provider failure',async({page})=>{
  await page.addInitScript(({key})=>localStorage.setItem(key,'dark'),{key:THEME_STORAGE_KEY});
  await page.route('https://tiles.openfreemap.org/**',route=>route.abort());
  await page.goto('/en/explore');await expect(page.locator('article')).toHaveCount(8);
  await expect(page.getByText(en.explore.mapUnavailable)).toBeVisible({timeout:15000});
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});

test("scenario codec round-trips Unicode and rejects malformed or unsupported inputs", () => {
  const original = structuredClone(scenario);
  original.candidates[0].name = "Квартира · Õismäe";
  expect(decodeScenario(encodeScenario(original))).toEqual(original);
  for (const mutate of [
    (s: Record<string, unknown>) => (s.version = 2),
    (s: Record<string, unknown>) => (s.currency = "USD"),
    (s: Record<string, unknown>) => (s.saved_at = "nonsense"),
    (s: Record<string, unknown>) =>
      (s.candidates = [...scenario.candidates, ...scenario.candidates]),
    (s: Record<string, unknown>) => (s.inject = "<script>"),
  ]) {
    const value = structuredClone(scenario) as unknown as Record<
      string,
      unknown
    >;
    mutate(value);
    expect(() => parseScenario(JSON.stringify(value))).toThrow();
  }
  for (const raw of ["", "not json", "x".repeat(17000)])
    expect(() => parseScenario(raw)).toThrow();
  const bad = structuredClone(scenario);
  bad.candidates[0].costs.rent = -1;
  expect(() => parseScenario(JSON.stringify(bad))).toThrow();
  bad.candidates[0].costs.rent = 650;
  bad.candidates[0].name = "<img onerror=x>";
  expect(() => parseScenario(JSON.stringify(bad))).toThrow();
  expect(() => decodeScenario("x".repeat(22001))).toThrow();
  expect(()=>parseScenario(JSON.stringify(scenario).replace('"user_bill"','["user_bill"]'))).toThrow();
});

test("review is required, comparison uses shared budget and unknown stays unknown", async ({
  page,
}) => {
  await page.goto(`/en/compare#plan=${encodeScenario(scenario)}`);
  await expect(page.getByTestId("scenario-review")).toBeVisible();
  await expect(page.getByTestId("comparison-card")).toHaveCount(0);
  await page
    .getByRole("button", { name: en.scenarios.apply, exact: true })
    .click();
  await expect(page.getByTestId("comparison-result")).toHaveCount(2);
  const cards = page.getByTestId("comparison-card");
  await expect(cards.first()).toContainText("€750.00");
  await expect(cards.first()).toContainText("€850.00");
  await expect(cards.first()).toContainText("€1,300.00");
  await expect(cards.nth(1)).toContainText("Unknown");
  expect(
    await page.evaluate((key) => localStorage.getItem(key), STORAGE_KEY),
  ).toBeNull();
  await page
    .getByRole("button", { name: en.scenarios.save, exact: true })
    .click();
  const raw = await page.evaluate(
    (key) => localStorage.getItem(key),
    STORAGE_KEY,
  );
  expect(parseScenario(raw!).budget).toEqual(scenario.budget);
  await page
    .getByRole("button", { name: en.scenarios.delete, exact: true })
    .click();
  expect(
    await page.evaluate((key) => localStorage.getItem(key), STORAGE_KEY),
  ).toBeNull();
});

test("private sharing omits gross, addresses and identifying names unless opted in", async ({
  page,
}) => {
  await importPlan(page);
  await page.getByText(en.scenarios.share, { exact: true }).click();
  await page.getByRole("button", { name: en.scenarios.preview }).click();
  await page.getByRole("button", { name: en.scenarios.generate }).click();
  const link = await page.getByLabel(en.scenarios.link).inputValue();
  const shared = decodeScenario(new URL(link).hash.slice(6));
  expect(shared.budget.income).toEqual({
    kind: "manual_net",
    net_monthly_income: 2409.76,
  });
  expect(shared.candidates[0].address).toBeNull();
  expect(shared.candidates[0].id).toBe('shared-1');
  expect(shared.candidates[0].name).toBe("Apartment A");
  await page.getByLabel(en.scenarios.includeAddress).check();
  await page.getByLabel(en.scenarios.includeGross).check();
  await page.getByRole("button", { name: en.scenarios.preview }).click();
  await page.getByRole("button", { name: en.scenarios.generate }).click();
  const explicit = decodeScenario(
    new URL(await page.getByLabel(en.scenarios.link).inputValue()).hash.slice(
      6,
    ),
  );
  expect(explicit.candidates[0].address).toBe("Mustamäe tee 5");
  expect(explicit.budget.income.kind).toBe("employment");
});

test("invalid stored plan never replaces working data and edited candidates recalculate", async ({
  page,
}) => {
  await importPlan(page);
  await page.evaluate(
    (key) => localStorage.setItem(key, '{"version":999}'),
    STORAGE_KEY,
  );
  await page
    .getByRole("button", { name: en.scenarios.load, exact: true })
    .click();
  await expect(page.getByText(en.scenarios.invalid)).toBeVisible();
  await expect(page.getByTestId("comparison-card")).toHaveCount(2);
  await page
    .getByTestId("comparison-card")
    .first()
    .getByRole("button", { name: "Edit", exact: true })
    .click();
  await page.getByLabel(en.apartment.fields.rent, { exact: true }).fill("700");
  await page.getByRole("button", { name: en.compare.confirm }).click();
  await expect(page.getByTestId("comparison-card").first()).toContainText(
    "€900.00",
  );
  await page.getByRole("button", { name: en.compare.add }).click();
  await page.getByLabel(en.compare.name, { exact: true }).fill("Third");
  await page.getByLabel(en.apartment.fields.rent, { exact: true }).fill("0");
  await page.getByRole("button", { name: en.compare.confirm }).click();
  await expect(page.getByTestId("comparison-card")).toHaveCount(3);
  await expect(
    page.getByRole("button", { name: en.compare.add }),
  ).toBeDisabled();
});

test("explore retains eight districts when map fails and passes options to comparison", async ({
  page,
}) => {
  await page.route("https://tiles.openfreemap.org/**", (r) => r.abort());
  await page.goto("/en/explore");
  await expect(page.locator("article")).toHaveCount(8);
  await expect(page.getByText(en.explore.mapUnavailable)).toBeVisible({
    timeout: 15000,
  });
  await page
    .getByRole("combobox", { name: en.explore.rooms, exact: true })
    .selectOption("2");
  await expect(page.locator("article")).toHaveCount(8);
  await page.getByRole("button", { name: en.explore.add }).first().click();
  await page.getByRole("link", { name: "Compare options (1/3)" }).click();
  await expect(page.getByTestId("comparison-card")).toHaveCount(1);
  await expect(page.getByTestId("comparison-card")).toContainText(
    en.apartment.unknownHint,
  );
});

test("comparison state and budget survive locale and route switches", async ({
  page,
}) => {
  await importPlan(page);
  await page.getByRole("link", { name: "ET", exact: true }).click();
  await expect(page.getByTestId("comparison-result")).toHaveCount(2);
  await page
    .getByRole("link", { name: et.compare.editBudget, exact: true })
    .click();
  await expect(page.locator("#planner-gross-income")).toHaveValue("3000");
  await expect(page.getByTestId("planner-results")).toBeVisible();
  await page.getByRole("link", { name: et.nav.compare, exact: true }).click();
  await expect(page.getByTestId("comparison-result")).toHaveCount(2);
});

test("budget failure preserves candidates and retry restores comparison", async ({
  page,
}) => {
  await importPlan(page);
  await page.route("**/api/v1/planner/budget", (r) =>
    r.fulfill({ status: 503, json: { detail: "unavailable" } }),
  );
  await page
    .getByTestId("comparison-card")
    .first()
    .getByRole("button", { name: "Edit", exact: true })
    .click();
  await page.getByLabel(en.apartment.fields.rent, { exact: true }).fill("700");
  await page.getByRole("button", { name: en.compare.confirm }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText(
    en.apartment.error,
  );
  await expect(page.getByTestId("comparison-result")).toHaveCount(0);
  await expect(page.getByTestId("comparison-card")).toHaveCount(2);
  await page.unroute("**/api/v1/planner/budget");
  await page
    .getByRole("button", { name: en.apartment.retry, exact: true })
    .click();
  await expect(page.getByTestId("comparison-result")).toHaveCount(2);
});

test('Russian layout keeps navigation, controls and comparison cards within bounds', async ({ page }) => {
  await importPlan(page, 'ru');
  for (const width of [320, 390, 768, 1024, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const navigation = await page.getByRole('navigation', { name: ru.a11y.mainNavigation }).boundingBox();
    const languages = await page.getByRole('navigation', { name: ru.languageSwitcher.label }).boundingBox();
    expect(navigation!.y, `menu below language controls at ${width}px`).toBeGreaterThanOrEqual(languages!.y + languages!.height);
    const overflowing = await page.locator('header, main').evaluateAll((roots) =>
      roots.flatMap((root) => [...root.querySelectorAll('button, a, article, input:not(.sr-only), select')])
        .filter((el) => {
          const rect = el.getBoundingClientRect();
          if (!rect.width || el.classList.contains('sr-only')) return false;
          return rect.right > document.documentElement.clientWidth + 1 || rect.left < -1 || el.scrollWidth > el.clientWidth + 2;
        }).map((el) => el.textContent?.trim() || el.tagName),
    );
    expect(overflowing, `unclipped Russian controls at ${width}px`).toEqual([]);
  }
  await page.screenshot({ path: 'test-results/ru-comparison-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 320, height: 900 });
  await page.screenshot({ path: 'test-results/ru-comparison-mobile.png', fullPage: true });
  for (const path of ['', '/planner', '/explore', '/calculator', '/housing', '/eresidency']) {
    await page.goto(`/ru${path}`);
    await expect(page.locator('main')).toHaveCount(1);
    await expect(page.locator('main')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `page width /ru${path}`).toBe(true);
  }
});

for (const [locale, messages] of Object.entries({ en, et, ru }))
  test(`comparison mobile accessibility and translations (${locale})`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await importPlan(page, locale);
    await expect(
      page.getByRole("heading", { name: messages.compare.title }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  });
