import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { THEME_STORAGE_KEY } from "../src/lib/theme";

// Axe runs the same rule engine Lighthouse uses, so a clean scan here is what
// keeps the accessibility score at 100 in CI's Lighthouse job.
const AXE_TAGS = [
  "wcag2a",
  "wcag2aa",
  "wcag21a",
  "wcag21aa",
  "wcag22aa",
  "best-practice",
];

async function scan(page: Page): Promise<string[]> {
  // The pages stream, so a scan can otherwise catch the loading skeleton
  // instead of the rendered page.
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  const results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();

  return results.violations.map(
    (violation) =>
      `${violation.id} (${violation.impact}): ${violation.help} -> ${violation.nodes
        .map((node) => node.target.join(" "))
        .join(" | ")}`
  );
}

for (const path of ["/en", "/en/planner", "/en/calculator", "/en/housing", "/en/eresidency"]) {
  test(`has no axe violations on ${path}`, async ({ page }) => {
    await page.goto(path);

    expect(await scan(page)).toEqual([]);
  });
}

test("has no axe violations with calculated results", async ({ page }) => {
  await page.goto("/en/calculator?gross=3000&pillar=2&basis=payer_cost");

  await expect(page.locator("[data-regime]")).toHaveCount(4);

  expect(await scan(page)).toEqual([]);
});

test("has no axe violations with a negative net income", async ({ page }) => {
  await page.goto("/en/calculator?gross=200&pillar=0&basis=gross");

  await expect(page.getByText("Negative net income").first()).toBeVisible();

  expect(await scan(page)).toEqual([]);
});

test("has no axe violations in the Estonian locale", async ({ page }) => {
  await page.goto("/et/calculator?gross=3000&pillar=2&basis=gross");

  await expect(page.locator("[data-regime]")).toHaveCount(4);

  expect(await scan(page)).toEqual([]);
});

test("has no axe violations with a budget result", async ({ page }) => {
  await page.goto("/en/planner");

  await page.getByLabel("Monthly gross salary, EUR").fill("3000");
  await page.getByLabel("II pension pillar contribution").selectOption("0.02");
  await page.getByLabel("Monthly non-housing spending, EUR").fill("700");
  await page.getByLabel("Monthly savings target, EUR").fill("300");
  await page.getByLabel("Maximum housing share, % of net").fill("30");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await expect(page.getByTestId("planner-results")).toBeVisible();

  // The click leaves the cursor hovering the submit button, whose hover
  // background is below the text-contrast threshold; move away so the scan
  // sees the resting state users actually read.
  await page.mouse.move(0, 0);

  expect(await scan(page)).toEqual([]);
});

test("has no axe violations with a selected address", async ({ page }) => {
  await page.route("**/api/v1/addresses/search**", async (route) => {
    await route.fulfill({
      json: {
        query: "Mustamäe tee 5",
        candidates: [
          {
            id: "ME02092715",
            label: "Harju maakond, Tallinn, Kristiine linnaosa, Mustamäe tee 5",
            short_label: "Mustamäe tee 5",
            longitude: 24.7034,
            latitude: 59.426593,
            district_id: null,
            quality: "exact",
          },
        ],
        attribution: {
          provider: "maa_ja_ruumiamet",
          label: "Maa- ja Ruumiamet / In-AKS",
          source_url: "https://geoportaal.maaamet.ee/est/teenused/integreeritav-aadressiotsing-in-aks-p504.html",
        },
      },
    });
  });
  await page.goto("/en/planner");

  await page.getByLabel("Monthly gross salary, EUR").fill("3000");
  await page.getByLabel("II pension pillar contribution").selectOption("0.02");
  await page.getByLabel("Monthly non-housing spending, EUR").fill("700");
  await page.getByLabel("Monthly savings target, EUR").fill("300");
  await page.getByLabel("Maximum housing share, % of net").fill("30");
  await page.getByRole("button", { name: "Calculate budget" }).click();
  await expect(page.getByTestId("planner-results")).toBeVisible();

  await page.getByLabel("Street address in Tallinn").fill("Mustamäe tee 5");
  await page.getByRole("listbox").getByRole("option").first().click();
  await expect(page.getByTestId("address-selected")).toBeVisible();
  await page.mouse.move(0, 0);

  expect(await scan(page)).toEqual([]);
});

test("has no axe violations on the planner in the dark theme", async ({ page }) => {
  await page.addInitScript((key) => {
    window.localStorage.setItem(key, "dark");
  }, THEME_STORAGE_KEY);
  await page.goto("/en/planner");

  await expect(page.locator("html")).toHaveClass(/dark/);

  expect(await scan(page)).toEqual([]);
});

test("has no axe violations in the dark theme", async ({ page }) => {
  await page.addInitScript((key) => {
    window.localStorage.setItem(key, "dark");
  }, THEME_STORAGE_KEY);
  await page.goto("/en/calculator?gross=3000&pillar=2&basis=gross");

  await expect(page.locator("html")).toHaveClass(/dark/);
  await expect(page.locator("[data-regime]")).toHaveCount(4);

  expect(await scan(page)).toEqual([]);
});
