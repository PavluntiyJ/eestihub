import { expect, test, type Locator } from "@playwright/test";

// Playwright can drive an input before React has hydrated it, after which the
// controlled value snaps back to its default. That is silent when the default
// happens to still produce a passing assertion, so every interaction that sets
// a value retries until the value actually sticks.
const STICK_TIMEOUT = 15_000;

async function fillStable(locator: Locator, value: string) {
  await expect(async () => {
    await locator.fill(value);
    await expect(locator).toHaveValue(value);
  }).toPass({ timeout: STICK_TIMEOUT });
}

async function selectStable(locator: Locator, value: string) {
  await expect(async () => {
    await locator.selectOption(value);
    await expect(locator).toHaveValue(value);
  }).toPass({ timeout: STICK_TIMEOUT });
}

async function checkStable(locator: Locator) {
  await expect(async () => {
    await locator.check();
    await expect(locator).toBeChecked();
  }).toPass({ timeout: STICK_TIMEOUT });
}

const districtNames = [
  "Haabersti",
  "Kesklinn",
  "Kristiine",
  "Lasnamäe",
  "Mustamäe",
  "Nõmme",
  "Pirita",
  "Põhja-Tallinn",
];

test("redirects to English home and shows API online", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/en$/);
  await expect(
    page.getByRole("heading", { name: "Plan your work, taxes, and next apartment in Estonia." })
  ).toBeVisible();
  await expect(page.getByText("online", { exact: true })).toBeVisible();
});

test("switches language to Estonian", async ({ page }) => {
  await page.goto("/en");

  await page.getByRole("link", { name: "ET" }).click();

  await expect(page).toHaveURL(/\/et$/);
  await expect(
    page.getByRole("heading", { name: "Planeeri oma tööd, makse ja järgmist kodu Eestis." })
  ).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "et");
});

test("navigates between feature pages and updates active section", async ({ page }) => {
  await page.goto("/en");

  await expect(page.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");

  await page.getByRole("link", { name: "Calculator" }).click();
  await expect(page).toHaveURL(/\/en\/calculator$/);
  await expect(page.getByRole("link", { name: "Calculator" })).toHaveAttribute(
    "aria-current",
    "page"
  );

  await page.getByRole("link", { name: "Rent" }).click();
  await expect(page).toHaveURL(/\/en\/housing$/);
  await expect(page.getByRole("link", { name: "Rent" })).toHaveAttribute("aria-current", "page");
});

test("calculates tax regimes from the form", async ({ page }) => {
  await page.goto("/en/calculator");

  await fillStable(page.getByLabel("Monthly gross income, EUR"), "3000");
  await selectStable(page.getByLabel("II pension pillar contribution"), "0.02");
  await page.getByRole("button", { name: "Calculate comparison" }).click();

  await expect(page.getByText("Monthly values returned by the tax API.")).toHaveCount(4);
  await expect(page.getByText("€2,409.76").first()).toBeVisible();
  await expect(page.getByText("Best net", { exact: true })).toBeVisible();
  await expect(page.getByText("Management board member").first()).toBeVisible();
  await expect(
    page.locator('[data-regime="juhatuse_liige"]').getByText("Best net", { exact: true })
  ).toBeVisible();

  await checkStable(page.locator('input[name="equalize_by"][value="payer_cost"]'));
  await page.getByRole("button", { name: "Calculate comparison" }).click();

  await expect(page.getByText("Active basis: Payer cost.")).toBeVisible();
  await expect(
    page.locator('[data-regime="ettevotluskonto"]').getByText("Best net", { exact: true })
  ).toBeVisible();
});

test("calculates e-residency first-year costs from navigation", async ({ page }) => {
  await page.goto("/en");

  await page.getByRole("link", { name: "e-Residency" }).click();
  await expect(page).toHaveURL(/\/en\/eresidency$/);
  await expect(
    page.getByRole("heading", { name: "Estimate your e-resident OÜ costs for year one." })
  ).toBeVisible();

  await fillStable(page.getByLabel("Expected monthly revenue, EUR"), "3000");
  await fillStable(page.getByLabel("Monthly accounting fee, EUR"), "75");
  await page.getByRole("button", { name: "Calculate first-year cost" }).click();

  await expect(page.getByTestId("first-year-total")).toHaveText("€1,615.00");
});

test("shows affordable districts and reacts to the housing share", async ({ page }) => {
  await page.goto("/en/calculator");

  await fillStable(page.getByLabel("Monthly gross income, EUR"), "3000");
  await page.getByRole("button", { name: "Calculate comparison" }).click();

  // CardTitle renders a div, not a heading, so match on text.
  await expect(page.getByText("Where you could rent", { exact: true })).toBeVisible();

  const districts = page.locator("[data-affordable-district]");
  const atThirty = await districts.count();
  expect(atThirty).toBeGreaterThan(0);

  // Widening the share can only ever afford more districts, never fewer.
  await fillStable(page.getByLabel(/Share of net income spent on housing/), "0.5");
  await expect
    .poll(async () => districts.count())
    .toBeGreaterThanOrEqual(atThirty);
});

test("renders a shared scenario URL without a submit", async ({ page }) => {
  await page.goto("/en/calculator?gross=3000&pillar=2&basis=payer_cost");

  await expect(page.locator("[data-regime]")).toHaveCount(4);
  await expect(page.getByText("Active basis: Payer cost.")).toBeVisible();
  await expect(
    page.locator('[data-regime="ettevotluskonto"]').getByText("Best net", { exact: true })
  ).toBeVisible();
  await expect(page.locator('input[name="gross_monthly_income"]')).toHaveValue("3000");
});

test("a malformed scenario URL falls back to the default form", async ({ page }) => {
  const response = await page.goto("/en/calculator?gross=abc&pillar=99&basis=nonsense");

  expect(response?.status()).toBe(200);
  await expect(page.locator("[data-regime]")).toHaveCount(0);
  await expect(page.locator('input[name="gross_monthly_income"]')).toHaveValue("3000");
});

test("submitting writes the scenario into the URL", async ({ page }) => {
  await page.goto("/en/calculator");

  await fillStable(page.locator('input[name="gross_monthly_income"]'), "2500");
  await checkStable(page.locator('input[name="equalize_by"][value="payer_cost"]'));
  await page.getByRole("button", { name: "Calculate comparison" }).click();

  await expect(page.locator("[data-regime]")).toHaveCount(4);
  await expect(page).toHaveURL(/gross=2500/);
  await expect(page).toHaveURL(/pillar=2/);
  await expect(page).toHaveURL(/basis=payer_cost/);
});

test("switching locale keeps the scenario", async ({ page }) => {
  await page.goto("/en/calculator?gross=3000&pillar=4&basis=gross");

  await page.getByRole("link", { name: "ET" }).click();

  await expect(page).toHaveURL(/\/et\/calculator\?/);
  await expect(page).toHaveURL(/gross=3000/);
  await expect(page).toHaveURL(/pillar=4/);
  await expect(page.locator("[data-regime]")).toHaveCount(4);
});

test("shows the entrepreneur-account annual-limit blocker", async ({ page }) => {
  await page.goto("/en/calculator");

  await fillStable(page.getByLabel("Monthly gross income, EUR"), "5000");
  await page.getByRole("button", { name: "Calculate comparison" }).click();

  await expect(
    page.getByText(
      "Annual receipts exceed €40,000. Register as an entrepreneur and VAT payer."
    )
  ).toBeVisible();
});

test("renders a negative FIE net without a full-width comparison bar", async ({ page }) => {
  await page.goto("/en/calculator");

  await fillStable(page.getByLabel("Monthly gross income, EUR"), "200");
  await selectStable(page.getByLabel("II pension pillar contribution"), "0");
  await page.getByRole("button", { name: "Calculate comparison" }).click();

  const fieComparison = page.locator('[data-regime-comparison="fie"]');
  const bestComparison = page.locator('[data-regime-comparison="juhatuse_liige"]');
  await expect(fieComparison.locator("[data-net-bar-fill]")).toHaveAttribute(
    "style",
    /width: 0%/
  );
  await expect(bestComparison.locator("[data-net-bar-fill]")).toHaveAttribute(
    "style",
    /width: 100%/
  );

  const fieCard = page.locator('[data-regime="fie"]');
  await expect(fieCard.getByText("Negative net income", { exact: true })).toBeVisible();
  await expect(fieCard.getByText("-€92.38", { exact: true })).toBeVisible();
  await expect(fieCard.getByText("146.2%", { exact: true })).toHaveCount(0);
});

test("accepts a comma decimal separator in every locale", async ({ page }) => {
  for (const locale of ["en", "et", "ru"]) {
    await page.goto(`/${locale}/calculator`);
    await fillStable(page.locator('input[name="gross_monthly_income"]'), "3000,50");
    await page.locator('form button[type="submit"]').click();

    await expect(page.locator('[data-regime="tooleping"]')).toBeVisible();
  }
});

test("shows housing table and chart", async ({ page }) => {
  await page.goto("/en/housing");

  await expect(page.getByRole("table").getByRole("row")).toHaveCount(9);

  for (const districtName of districtNames) {
    await expect(page.getByRole("cell", { name: districtName })).toBeVisible();
  }

  await expect(page.getByText("Average 2-room rent")).toBeVisible();
  await expect(page.locator("svg").first()).toBeVisible();
});

test("disables calculator submit for invalid income", async ({ page }) => {
  await page.goto("/en/calculator");

  await fillStable(page.getByLabel("Monthly gross income, EUR"), "");

  await expect(page.getByRole("button", { name: "Calculate comparison" })).toBeDisabled();
  await expect(page.getByText("Enter an amount greater than 0.")).toBeVisible();
});
