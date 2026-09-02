import { expect, test } from "@playwright/test";

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

  await page.getByLabel("Monthly gross income, EUR").fill("3000");
  await page.getByLabel("II pension pillar contribution").selectOption("0.02");
  await page.getByRole("button", { name: "Calculate comparison" }).click();

  await expect(page.getByText("Monthly values returned by the tax API.")).toHaveCount(4);
  await expect(page.getByText("€2,409.76").first()).toBeVisible();
  await expect(page.getByText("Best net", { exact: true })).toBeVisible();
  await expect(page.getByText("Management board member").first()).toBeVisible();
  await expect(
    page.locator('[data-regime="juhatuse_liige"]').getByText("Best net", { exact: true })
  ).toBeVisible();

  await page.getByLabel("Payer cost").check();
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

  await page.getByLabel("Expected monthly revenue, EUR").fill("3000");
  await page.getByLabel("Monthly accounting fee, EUR").fill("75");
  await page.getByRole("button", { name: "Calculate first-year cost" }).click();

  await expect(page.getByTestId("first-year-total")).toHaveText("€1,615.00");
});

test("shows affordable districts and reacts to the housing share", async ({ page }) => {
  await page.goto("/en/calculator");

  await page.getByLabel("Monthly gross income, EUR").fill("3000");
  await page.getByRole("button", { name: "Calculate comparison" }).click();

  // CardTitle renders a div, not a heading, so match on text.
  await expect(page.getByText("Where you could rent", { exact: true })).toBeVisible();

  const districts = page.locator("[data-affordable-district]");
  const atThirty = await districts.count();
  expect(atThirty).toBeGreaterThan(0);

  // Widening the share can only ever afford more districts, never fewer.
  await page.getByLabel(/Share of net income spent on housing/).fill("0.5");
  await expect
    .poll(async () => districts.count())
    .toBeGreaterThanOrEqual(atThirty);
});

test("shows the entrepreneur-account annual-limit blocker", async ({ page }) => {
  await page.goto("/en/calculator");

  await page.getByLabel("Monthly gross income, EUR").fill("5000");
  await page.getByRole("button", { name: "Calculate comparison" }).click();

  await expect(
    page.getByText(
      "Annual receipts exceed €40,000. Register as an entrepreneur and VAT payer."
    )
  ).toBeVisible();
});

test("renders a negative FIE net without a full-width comparison bar", async ({ page }) => {
  await page.goto("/en/calculator");

  await page.getByLabel("Monthly gross income, EUR").fill("200");
  await page.getByLabel("II pension pillar contribution").selectOption("0");
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
    await page.locator('input[name="gross_monthly_income"]').fill("3000,50");
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

  await page.getByLabel("Monthly gross income, EUR").fill("");

  await expect(page.getByRole("button", { name: "Calculate comparison" })).toBeDisabled();
  await expect(page.getByText("Enter an amount greater than 0.")).toBeVisible();
});
