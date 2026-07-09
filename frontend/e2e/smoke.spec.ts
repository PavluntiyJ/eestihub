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
