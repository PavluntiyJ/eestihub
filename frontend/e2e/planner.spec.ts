import { expect, test, type Locator, type Page } from "@playwright/test";

// Same hydration race as the calculator smokes: retry the fill until the
// controlled value actually sticks.
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

async function fillEmploymentBudget(
  page: Page,
  gross = "3000",
  pension = "0.02",
  spending = "700",
  savings = "300",
  share = "30"
) {
  await fillStable(page.getByLabel("Monthly gross salary, EUR"), gross);
  await selectStable(page.getByLabel("II pension pillar contribution"), pension);
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), spending);
  await fillStable(page.getByLabel("Monthly savings target, EUR"), savings);
  await fillStable(page.getByLabel("Maximum housing share, % of net"), share);
  await page.getByRole("button", { name: "Calculate budget" }).click();
}

test("links the planner from navigation and the home page", async ({ page }) => {
  await page.goto("/en");

  await page.getByRole("link", { name: "Plan my budget", exact: true }).click();
  await expect(page).toHaveURL(/\/en\/planner$/);
  await expect(
    page.getByRole("heading", { name: "From salary to housing allowance." })
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Planner", exact: true })).toHaveAttribute(
    "aria-current",
    "page"
  );
});

test("calculates a budget from employment income", async ({ page }) => {
  await page.goto("/en/planner");

  await fillEmploymentBudget(page);

  await expect(page.getByTestId("planner-results")).toBeVisible();
  await expect(page.getByTestId("planner-net")).toHaveText("€2,409.76");
  await expect(page.getByTestId("planner-tax-year")).toHaveText("2026");
  await expect(page.getByTestId("planner-allowance")).toHaveText("€722.93");
  await expect(page.getByTestId("planner-available")).toHaveText("€1,409.76");
  await expect(page.getByTestId("planner-share-limit")).toContainText("€722.93");
});

test("calculates a budget from manual net income", async ({ page }) => {
  await page.goto("/en/planner");

  await page.getByLabel("Manual net income").check();
  await fillStable(page.getByLabel("Monthly net income, EUR"), "2400");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "700");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "300");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "35");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await expect(page.getByTestId("planner-results")).toBeVisible();
  await expect(page.getByTestId("planner-net")).toHaveText("€2,400.00");
  await expect(page.getByTestId("planner-tax-year")).toHaveText("Not applicable");
  await expect(page.getByTestId("planner-allowance")).toHaveText("€840.00");
});

test("validates before calling the API and focuses the first error", async ({ page }) => {
  let apiCalls = 0;
  await page.route("**/api/v1/planner/budget", async (route) => {
    apiCalls += 1;
    await route.continue();
  });
  await page.goto("/en/planner");

  await page.getByRole("button", { name: "Calculate budget" }).click();

  await expect(page.getByText("Enter a gross salary greater than 0")).toBeVisible();
  await expect(page.locator("#planner-gross-income")).toBeFocused();
  await expect(page.getByTestId("planner-results")).toHaveCount(0);
  expect(apiCalls).toBe(0);
});

test("rejects a blank manual net without calling the API", async ({ page }) => {
  let apiCalls = 0;
  await page.route("**/api/v1/planner/budget", async (route) => {
    apiCalls += 1;
    await route.continue();
  });
  await page.goto("/en/planner");

  await page.getByLabel("Manual net income").check();
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "700");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "300");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "35");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await expect(page.getByText("Enter a net income of 0 or more")).toBeVisible();
  await expect(page.locator("#planner-net-income")).toBeFocused();
  await expect(page.getByTestId("planner-results")).toHaveCount(0);
  expect(apiCalls).toBe(0);
});

test("rejects blank spending and savings without calling the API", async ({ page }) => {
  let apiCalls = 0;
  await page.route("**/api/v1/planner/budget", async (route) => {
    apiCalls += 1;
    await route.continue();
  });
  await page.goto("/en/planner");

  await fillStable(page.getByLabel("Monthly gross salary, EUR"), "3000");
  await selectStable(page.getByLabel("II pension pillar contribution"), "0.02");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await expect(page.getByText("Enter spending of 0 or more")).toBeVisible();
  await expect(page.getByText("Enter a savings target of 0 or more")).toBeVisible();
  await expect(page.locator("#planner-spending")).toBeFocused();
  await expect(page.getByTestId("planner-results")).toHaveCount(0);
  expect(apiCalls).toBe(0);
});

test("rejects a blank share without calling the API", async ({ page }) => {
  let apiCalls = 0;
  await page.route("**/api/v1/planner/budget", async (route) => {
    apiCalls += 1;
    await route.continue();
  });
  await page.goto("/en/planner");

  await fillStable(page.getByLabel("Monthly gross salary, EUR"), "3000");
  await selectStable(page.getByLabel("II pension pillar contribution"), "0.02");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "700");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "300");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await expect(page.getByText("Enter a share from 0 to 100.")).toBeVisible();
  await expect(page.locator("#planner-share")).toBeFocused();
  await expect(page.getByTestId("planner-results")).toHaveCount(0);
  expect(apiCalls).toBe(0);
});

test("serializes fractional shares without float artifacts", async ({ page }) => {
  await page.goto("/en/planner");

  await fillStable(page.getByLabel("Monthly gross salary, EUR"), "3000");
  await selectStable(page.getByLabel("II pension pillar contribution"), "0.02");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "700");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "300");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "33.34");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  // 33.34% / 100 must reach the API as 0.3334, not 0.33340000000000003.
  await expect(page.getByTestId("planner-allowance")).toHaveText("€803.41");

  await fillStable(page.getByLabel("Maximum housing share, % of net"), "35.01");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await expect(page.getByTestId("planner-allowance")).toHaveText("€843.66");
});

test("accepts zero spending and savings", async ({ page }) => {
  await page.goto("/en/planner");

  await page.getByLabel("Manual net income").check();
  await fillStable(page.getByLabel("Monthly net income, EUR"), "2000");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "0");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "0");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "50");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await expect(page.getByTestId("planner-allowance")).toHaveText("€1,000.00");
});

test("shows a signed deficit instead of a celebration", async ({ page }) => {
  await page.goto("/en/planner");

  await page.getByLabel("Manual net income").check();
  await fillStable(page.getByLabel("Monthly net income, EUR"), "1200");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "1000");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "300");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "35");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await expect(page.getByTestId("planner-available")).toHaveText("-€100.00");
  await expect(page.getByTestId("planner-allowance")).toHaveText("€0.00");
  await expect(page.getByTestId("planner-deficit")).toBeVisible();
});

test("marks results stale after edits", async ({ page }) => {
  await page.goto("/en/planner");

  await fillEmploymentBudget(page);
  await expect(page.getByTestId("planner-results")).toBeVisible();
  await expect(page.getByTestId("planner-stale")).toHaveCount(0);

  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "800");

  await expect(page.getByTestId("planner-stale")).toBeVisible();
  // The previous numbers stay on screen while marked outdated.
  await expect(page.getByTestId("planner-allowance")).toHaveText("€722.93");
});

test("ignores stale responses in submission order", async ({ page }) => {
  let delayedOnce = false;
  await page.route("**/api/v1/planner/budget", async (route) => {
    try {
      if (!delayedOnce) {
        delayedOnce = true;
        await page.waitForTimeout(600);
      }
      await route.continue();
    } catch {
      // The first request is aborted by the second submit; nothing to forward.
    }
  });
  await page.goto("/en/planner");

  await fillStable(page.getByLabel("Monthly gross salary, EUR"), "3000");
  await selectStable(page.getByLabel("II pension pillar contribution"), "0.02");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "700");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "300");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "30");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await fillStable(page.getByLabel("Monthly gross salary, EUR"), "4000");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  // The slower first response must not overwrite the second one.
  await expect(page.getByTestId("planner-net")).toHaveText("€3,161.68");
});

test("retries after a failure and preserves inputs", async ({ page }) => {
  let failedOnce = false;
  await page.route("**/api/v1/planner/budget", async (route) => {
    if (!failedOnce) {
      failedOnce = true;
      await route.abort();
      return;
    }
    await route.continue();
  });
  await page.goto("/en/planner");

  await fillEmploymentBudget(page);

  await expect(page.getByTestId("planner-error")).toBeVisible();
  await expect(page.locator("#planner-gross-income")).toHaveValue("3000");
  await expect(page.getByTestId("planner-results")).toHaveCount(0);

  await page.getByRole("button", { name: "Retry calculation" }).click();

  await expect(page.getByTestId("planner-net")).toHaveText("€2,409.76");
  await expect(page.getByTestId("planner-error")).toHaveCount(0);
});

test("operates by keyboard alone", async ({ page }) => {
  await page.goto("/en/planner");

  await page.locator("#planner-gross-income").focus();
  await page.keyboard.type("3000");
  await page.keyboard.press("Tab");
  await page.keyboard.type("2");
  await page.keyboard.press("Tab");
  await page.keyboard.type("700");
  await page.keyboard.press("Tab");
  await page.keyboard.type("300");
  await page.keyboard.press("Tab");
  await page.keyboard.type("30");
  await page.keyboard.press("Enter");

  await expect(page.getByTestId("planner-net")).toHaveText("€2,409.76");
});

test("works on a mobile viewport without horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/en/planner");

  await fillEmploymentBudget(page);

  await expect(page.getByTestId("planner-allowance")).toHaveText("€722.93");
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("renders the planner in Estonian and Russian", async ({ page }) => {
  await page.goto("/et/planner");
  await expect(
    page.getByRole("heading", { name: "Palgast eluasemetoetuseni." })
  ).toBeVisible();

  await fillStable(page.getByLabel("Kuu brutopalk, EUR"), "3000");
  await selectStable(page.getByLabel("II pensionisamba makse"), "0.02");
  await fillStable(page.getByLabel("Kuu eluasemevälised kulud, EUR"), "700");
  await fillStable(page.getByLabel("Kuu säästueesmärk, EUR"), "300");
  await fillStable(page.getByLabel("Eluaseme maksimaalne osakaal, % netost"), "30");
  await page.getByRole("button", { name: "Arvuta eelarve" }).click();
  await expect(page.getByTestId("planner-results")).toBeVisible();

  await page.goto("/ru/planner");
  await expect(
    page.getByRole("heading", { name: "От зарплаты до жилищного бюджета." })
  ).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
});

test("warns before locale navigation discards an unsaved draft", async ({ page }) => {
  await page.goto("/en/planner");

  await fillStable(page.getByLabel("Monthly gross salary, EUR"), "3000");

  // Dismissing the confirm keeps the draft in place.
  page.once("dialog", (dialog) => void dialog.dismiss());
  await page.getByRole("link", { name: "ET", exact: true }).click();
  await expect(page).toHaveURL(/\/en\/planner$/);
  await expect(page.locator("#planner-gross-income")).toHaveValue("3000");

  // Accepting the confirm navigates; client state is reset by design.
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("link", { name: "ET", exact: true }).click();
  await expect(page).toHaveURL(/\/et\/planner$/);
});

test("warns on locale navigation even after a fresh result", async ({ page }) => {
  await page.goto("/en/planner");

  await page.getByLabel("Manual net income").check();
  await fillStable(page.getByLabel("Monthly net income, EUR"), "2400");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "700");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "300");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "35");
  await page.getByRole("button", { name: "Calculate budget" }).click();
  await expect(page.getByTestId("planner-allowance")).toHaveText("€840.00");

  // Dismissing keeps the calculated draft: inputs and result stay intact.
  page.once("dialog", (dialog) => void dialog.dismiss());
  await page.getByRole("link", { name: "ET", exact: true }).click();
  await expect(page).toHaveURL(/\/en\/planner$/);
  await expect(page.locator("#planner-net-income")).toHaveValue("2400");
  await expect(page.getByTestId("planner-allowance")).toHaveText("€840.00");

  // Accepting navigates; client state resets by design.
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("link", { name: "ET", exact: true }).click();
  await expect(page).toHaveURL(/\/et\/planner$/);
});

test("lets the second response win while the first is held", async ({ page }) => {
  const firstResponse = {
    schema_version: 1,
    income: { kind: "manual_net", net_monthly_income: 1000.0, tax_year: null },
    budget: {
      monthly_non_housing: 700.0,
      monthly_savings: 300.0,
      housing_share: 0.35,
      available_after_commitments: 0.0,
      share_limit: 350.0,
      housing_allowance: 0.0,
    },
    apartment: null,
    warnings: [],
  };
  const secondResponse = {
    schema_version: 1,
    income: { kind: "manual_net", net_monthly_income: 2000.0, tax_year: null },
    budget: {
      monthly_non_housing: 700.0,
      monthly_savings: 300.0,
      housing_share: 0.35,
      available_after_commitments: 1000.0,
      share_limit: 700.0,
      housing_allowance: 700.0,
    },
    apartment: null,
    warnings: [],
  };

  let releaseFirst!: () => void;
  const gate = new Promise<void>((resolve) => {
    releaseFirst = resolve;
  });
  let calls = 0;
  await page.route("**/api/v1/planner/budget", async (route) => {
    calls += 1;

    try {
      if (calls === 1) {
        await gate;
        await route.fulfill({ json: firstResponse });
      } else {
        await route.fulfill({ json: secondResponse });
      }
    } catch {
      // Editing aborts the held request; nothing left to answer.
    }
  });
  await page.goto("/en/planner");

  await page.getByLabel("Manual net income").check();
  await fillStable(page.getByLabel("Monthly net income, EUR"), "1000");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "700");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "300");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "35");
  await page.getByRole("button", { name: "Calculate budget" }).click();

  await fillStable(page.getByLabel("Monthly net income, EUR"), "2000");
  // The first submit is still in flight, so the button reads "Calculating..."
  // and stays enabled for the superseding submission.
  await page.getByRole("button", { name: /calculat/i }).click();

  // Request two completes while request one is still held.
  await expect(page.getByTestId("planner-allowance")).toHaveText("€700.00");

  releaseFirst();
  await expect.poll(() => calls).toBe(2);

  // The late first response must not overwrite the fresher numbers.
  await expect(page.getByTestId("planner-allowance")).toHaveText("€700.00");
});

test("links the housing overview as general context", async ({ page }) => {
  await page.goto("/en/planner");

  await fillEmploymentBudget(page);

  // The calculated draft is unsaved client state, so leaving confirms first.
  page.once("dialog", (dialog) => void dialog.accept());
  await page
    .getByRole("link", { name: "See Tallinn district averages as general context" })
    .click();
  await expect(page).toHaveURL(/\/en\/housing$/);
});
