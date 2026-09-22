import { expect, test, type Locator, type Page } from "@playwright/test";

// The address input is a controlled field like the calculator ones: retry
// the fill until the value actually sticks after hydration.
const STICK_TIMEOUT = 15_000;

async function fillStable(locator: Locator, value: string) {
  await expect(async () => {
    await locator.fill(value);
    await expect(locator).toHaveValue(value);
  }).toPass({ timeout: STICK_TIMEOUT });
}

const ATTRIBUTION = {
  provider: "maa_ja_ruumiamet",
  label: "Maa- ja Ruumiamet / In-AKS",
  source_url: "https://geoportaal.maaamet.ee/est/teenused/integreeritav-aadressiotsing-in-aks-p504.html",
};

const MUSTAMAE_FIXTURE = {
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
    {
      id: "ME00648668",
      label: "Harju maakond, Tallinn, Kristiine linnaosa, Mustamäe tee 5a",
      short_label: "Mustamäe tee 5a",
      longitude: 24.704843,
      latitude: 59.427357,
      district_id: null,
      quality: "partial",
    },
  ],
  attribution: ATTRIBUTION,
};

const TARTU_FIXTURE = {
  query: "Tartu mnt 1",
  candidates: [
    {
      id: "EE04064863",
      label: "Harju maakond, Tallinn, Kesklinna linnaosa, Tartu mnt 1",
      short_label: "Tartu mnt 1",
      longitude: 24.758626,
      latitude: 59.435048,
      district_id: null,
      quality: "exact",
    },
  ],
  attribution: ATTRIBUTION,
};

async function mockAddresses(page: Page, fixture: unknown, calls?: string[]) {
  await page.route("**/api/v1/addresses/search**", async (route) => {
    if (calls) {
      calls.push(route.request().url());
    }
    await route.fulfill({ json: fixture });
  });
}

async function calculateBudget(page: Page) {
  await fillStable(page.getByLabel("Monthly gross salary, EUR"), "3000");
  await page.getByLabel("II pension pillar contribution").selectOption("0.02");
  await fillStable(page.getByLabel("Monthly non-housing spending, EUR"), "700");
  await fillStable(page.getByLabel("Monthly savings target, EUR"), "300");
  await fillStable(page.getByLabel("Maximum housing share, % of net"), "30");
  await page.getByRole("button", { name: "Calculate budget" }).click();
  await expect(page.getByTestId("planner-results")).toBeVisible();
}

test("debounces automatic search into a single request", async ({ page }) => {
  const calls: string[] = [];
  await mockAddresses(page, MUSTAMAE_FIXTURE, calls);
  await page.goto("/en/planner");
  await calculateBudget(page);

  const input = page.getByLabel("Street address in Tallinn");
  await fillStable(input, "Must");
  await page.waitForTimeout(200);
  await fillStable(input, "Mustamäe tee 5");

  await expect(page.getByRole("listbox").getByRole("option").first()).toBeVisible();
  expect(calls).toHaveLength(1);
  expect(calls[0]).toContain("q=Mustam%C3%A4e+tee+5");
});

test("searches explicitly from three characters", async ({ page }) => {
  const calls: string[] = [];
  await mockAddresses(page, MUSTAMAE_FIXTURE, calls);
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "tee");
  await page.getByRole("button", { name: "Search addresses" }).click();

  await expect(page.getByRole("listbox").getByRole("option").first()).toBeVisible();
  // The pending debounce must not fire the same search a second time.
  await page.waitForTimeout(800);
  expect(calls).toHaveLength(1);
});

test("clearing a pending input drops the late response", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/addresses/search**", async (route) => {
    try {
      await gate;
      await route.fulfill({ json: TARTU_FIXTURE });
    } catch {
      // The edit aborts the held request; nothing left to answer.
    }
  });
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Tartu mnt 1");
  await page.waitForRequest("**/api/v1/addresses/search**");
  await fillStable(page.getByLabel("Street address in Tallinn"), "");

  release();
  await page.waitForTimeout(300);

  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(page.getByTestId("address-selected")).toHaveCount(0);
  await expect(page.getByLabel("Street address in Tallinn")).toHaveValue("");
});

test("shortening a pending input below threshold drops the late response", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/addresses/search**", async (route) => {
    try {
      await gate;
      await route.fulfill({ json: TARTU_FIXTURE });
    } catch {
      // The edit aborts the held request; nothing left to answer.
    }
  });
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Tartu mnt 1");
  await page.waitForRequest("**/api/v1/addresses/search**");
  await fillStable(page.getByLabel("Street address in Tallinn"), "Tar");

  release();
  await page.waitForTimeout(300);

  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(page.getByTestId("address-selected")).toHaveCount(0);
});

test("selecting an option schedules no follow-up search", async ({ page }) => {
  const calls: string[] = [];
  await mockAddresses(page, MUSTAMAE_FIXTURE, calls);
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustam");
  await expect(page.getByRole("listbox").getByRole("option")).toHaveCount(2);
  await page.getByRole("listbox").getByRole("option").nth(1).click();

  await expect(page.getByTestId("address-selected")).toContainText("Mustamäe tee 5a");
  await expect(page.getByRole("listbox")).toHaveCount(0);

  // The rewritten label must not schedule a search of its own text.
  await page.waitForTimeout(900);
  expect(calls).toHaveLength(1);
});

test("a held request times out with retry", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/addresses/search**", async (route) => {
    try {
      await gate;
      await route.fulfill({ json: MUSTAMAE_FIXTURE });
    } catch {
      // The client timeout aborts the held request; nothing left to answer.
    }
  });
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 5");

  // The 10-second client bound surfaces the retry state on a hanging call.
  await expect(page.getByText("Address search is unavailable right now.")).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByLabel("Street address in Tallinn")).toHaveValue("Mustamäe tee 5");
  await expect(page.getByTestId("planner-allowance")).toHaveText("€722.93");

  release();
  await page.waitForTimeout(300);

  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Retry search" })).toBeVisible();
});

test("selects an address with the keyboard and shows context", async ({ page }) => {
  await mockAddresses(page, MUSTAMAE_FIXTURE);
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 5");
  await expect(page.getByRole("listbox").getByRole("option")).toHaveCount(2);

  await page.locator("#address-search-input").press("ArrowDown");
  await page.locator("#address-search-input").press("Enter");

  const selected = page.getByTestId("address-selected");
  await expect(selected).toBeVisible();
  await expect(
    selected.getByText("Harju maakond, Tallinn, Kristiine linnaosa, Mustamäe tee 5")
  ).toBeVisible();
  // The announcement keeps the search hit count after the dropdown clears.
  await expect(page.getByText("2 matching addresses found.")).toBeVisible();
  await expect(selected.getByText(/24\.7034/)).toBeVisible();
  await expect(
    selected.getByText("Location context only", { exact: false })
  ).toBeVisible();
  // The budget numbers are untouched by the selection.
  await expect(page.getByTestId("planner-allowance")).toHaveText("€722.93");
  await expect(page.getByTestId("address-attribution")).toContainText(
    "Maa- ja Ruumiamet / In-AKS"
  );
});

test("editing or clearing text drops the selection immediately", async ({ page }) => {
  await mockAddresses(page, MUSTAMAE_FIXTURE);
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 5");
  await page.getByRole("listbox").getByRole("option").first().click();
  await expect(page.getByTestId("address-selected")).toBeVisible();

  await page.getByRole("button", { name: "Clear selected address" }).click();
  await expect(page.getByLabel("Street address in Tallinn")).toHaveValue("");
  await expect(page.getByTestId("address-selected")).toHaveCount(0);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 5");
  await page.getByRole("listbox").getByRole("option").first().click();
  await expect(page.getByTestId("address-selected")).toBeVisible();

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 50");
  await expect(page.getByTestId("address-selected")).toHaveCount(0);
});

test("ignores a late first response", async ({ page }) => {
  let releaseFirst!: () => void;
  const gate = new Promise<void>((resolve) => {
    releaseFirst = resolve;
  });
  let calls = 0;
  await page.route("**/api/v1/addresses/search**", async (route) => {
    calls += 1;

    try {
      if (calls === 1) {
        await gate;
        await route.fulfill({ json: MUSTAMAE_FIXTURE });
      } else {
        await route.fulfill({ json: TARTU_FIXTURE });
      }
    } catch {
      // Editing aborts the held request; nothing left to answer.
    }
  });
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 5");
  // The first request must be in flight (held at the gate) before the edit,
  // or debounce would swallow it and the ordering proves nothing.
  await page.waitForRequest("**/api/v1/addresses/search**");
  await fillStable(page.getByLabel("Street address in Tallinn"), "Tartu mnt 1");

  await expect(page.getByRole("listbox").getByRole("option", { name: /Tartu mnt 1/ }).first()).toBeVisible();

  releaseFirst();
  await expect.poll(() => calls).toBe(2);

  await expect(page.getByRole("listbox").getByRole("option", { name: /Tartu mnt 1/ })).toHaveCount(1);
  await expect(page.getByRole("listbox").getByRole("option", { name: /Mustamäe/ })).toHaveCount(0);
});

test("retries after a failure and preserves query and budget", async ({ page }) => {
  let failedOnce = false;
  await page.route("**/api/v1/addresses/search**", async (route) => {
    if (!failedOnce) {
      failedOnce = true;
      await route.abort();
      return;
    }
    await route.fulfill({ json: MUSTAMAE_FIXTURE });
  });
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 5");

  await expect(page.getByText("Address search is unavailable right now.")).toBeVisible();
  await expect(page.getByLabel("Street address in Tallinn")).toHaveValue("Mustamäe tee 5");
  await expect(page.getByTestId("planner-allowance")).toHaveText("€722.93");

  await page.getByRole("button", { name: "Retry search" }).click();

  await expect(page.getByRole("listbox").getByRole("option").first()).toBeVisible();
});

test("shows an empty state for no matches", async ({ page }) => {
  await mockAddresses(page, {
    query: "Nope street 1",
    candidates: [],
    attribution: ATTRIBUTION,
  });
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Nope street 1");

  await expect(page.getByText("No Tallinn addresses match.")).toBeVisible();
  await expect(page.getByTestId("planner-allowance")).toHaveText("€722.93");
});

test("shows a distinct busy state", async ({ page }) => {
  await page.route("**/api/v1/addresses/search**", async (route) => {
    await route.fulfill({
      status: 503,
      json: { detail: { code: "address_search_busy" } },
    });
  });
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 5");

  await expect(page.getByText("Address search is busy.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry search" })).toBeVisible();
});

test("searches addresses in Estonian", async ({ page }) => {
  await mockAddresses(page, MUSTAMAE_FIXTURE);
  await page.goto("/et/planner");
  await expect(
    page.getByRole("heading", { name: "Palgast eluasemetoetuseni." })
  ).toBeVisible();

  await fillStable(page.getByLabel("Kuu brutopalk, EUR"), "3000");
  await page.getByLabel("II pensionisamba makse").selectOption("0.02");
  await fillStable(page.getByLabel("Kuu eluasemevälised kulud, EUR"), "700");
  await fillStable(page.getByLabel("Kuu säästueesmärk, EUR"), "300");
  await fillStable(page.getByLabel("Eluaseme maksimaalne osakaal, % netost"), "30");
  await page.getByRole("button", { name: "Arvuta eelarve" }).click();
  await expect(page.getByTestId("planner-results")).toBeVisible();

  await fillStable(page.getByLabel("Tallinna tänava-aadress"), "Mustamäe tee 5");
  await page.getByRole("listbox").getByRole("option").first().click();

  await expect(page.getByTestId("address-selected")).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "et");
});

test("works on a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockAddresses(page, MUSTAMAE_FIXTURE);
  await page.goto("/en/planner");
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 5");
  await page.getByRole("listbox").getByRole("option").first().click();

  await expect(page.getByTestId("address-selected")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("works in the dark theme", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("eestihub-theme", "dark");
  });
  await mockAddresses(page, MUSTAMAE_FIXTURE);
  await page.goto("/en/planner");

  await expect(page.locator("html")).toHaveClass(/dark/);
  await calculateBudget(page);

  await fillStable(page.getByLabel("Street address in Tallinn"), "Mustamäe tee 5");
  await page.getByRole("listbox").getByRole("option").first().click();

  await expect(page.getByTestId("address-selected")).toBeVisible();
});
