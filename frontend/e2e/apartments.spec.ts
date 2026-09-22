import {expect, test, type Page} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import en from "../src/messages/en.json";
import et from "../src/messages/et.json";
import ru from "../src/messages/ru.json";

const candidate = {id: "ME02092715", label: "Tallinn, Mustamäe tee 5", short_label: "Mustamäe tee 5",
  latitude: 59.426593, longitude: 24.7034, district_id: null, quality: "exact"};
const nearby = {
  radius_m: 800, limit: 20, timezone: "Europe/Tallinn", service_date: "2026-09-22",
  stops: [{id: "001", name: "Marja", longitude: 24.703, latitude: 59.427,
    straight_line_distance_m: 52, routes: [{id: "R1", short_name: "16", long_name: "Marja route", mode: "bus"}]},
    {id: "002", name: "Marja", longitude: 24.704, latitude: 59.428,
      straight_line_distance_m: 170, routes: []}],
  feed: {source_url: "https://transport.tallinn.ee/data/gtfs.zip", attribution: "Tallinn GTFS timetable",
    license_url: "https://creativecommons.org/licenses/by-sa/3.0/", data_license: "CC-BY-SA-3.0",
    transformation: "Stops joined with scheduled routes", fetched_at: "2026-09-22T10:00:00Z",
    checked_at: "2026-09-22T10:00:00Z", source_last_modified: "2026-09-18T12:29:00Z",
    calendar_start: "2026-01-01", calendar_end: "2027-01-01", freshness: "current"},
};

async function budget(page: Page, locale = "en") {
  await page.goto(`/${locale}/planner`);
  await page.locator('input[value="manual_net"]').check();
  for (const [id, value] of [["net-income", "2400"], ["spending", "700"], ["savings", "300"], ["share", "35"]]) {
    await expect(async () => {
      await page.locator(`#planner-${id}`).fill(value);
      await expect(page.locator(`#planner-${id}`)).toHaveValue(value);
    }).toPass();
  }
  await page.locator("form").first().locator('button[type="submit"]').click();
  await expect(page.getByTestId("apartment-assessment")).toBeVisible();
}

async function costs(page: Page) {
  await page.locator("#apartment-rent").fill("650");
  await page.locator("#apartment-summer").fill("100");
  await page.locator("#apartment-winter").fill("200");
  await page.getByTestId("assess-apartment").click();
  await expect(page.getByTestId("apartment-result")).toBeVisible();
}

async function address(page: Page) {
  await page.route("**/api/v1/addresses/search**", route => route.fulfill({json: {
    query: "Mustamäe tee 5", candidates: [candidate], attribution: {provider: "maa_ja_ruumiamet",
      label: "Maa- ja Ruumiamet / In-AKS", source_url: "https://geoportaal.maaamet.ee/"},
  }}));
  await page.getByRole("combobox", {name: "Street address in Tallinn"}).fill("Mustamäe tee 5");
  await page.getByRole("option", {name: /Tallinn, Mustamäe tee 5/}).click();
  await expect(page.getByTestId("location-context")).toBeVisible();
}

test("assesses seasonal costs and distinguishes unknown move-in costs from zero", async ({page}) => {
  await budget(page);
  await costs(page);
  await expect(page.getByText("Fits in one season only", {exact: true})).toBeVisible();
  await expect(page.getByTestId("summer-total")).toHaveText("€750.00");
  await expect(page.getByTestId("winter-total")).toHaveText("€850.00");
  await expect(page.getByTestId("summer-remainder")).toHaveText("€650.00");
  await expect(page.getByTestId("winter-remainder")).toHaveText("€550.00");
  await expect(page.getByTestId("move-in-total")).toHaveText("Unknown");
  await page.locator("summary").filter({hasText: "Cash needed to move in"}).click();
  for (const key of ["deposit", "broker_fee", "setup"]) await page.locator(`#apartment-${key}`).fill(key === "deposit" ? "650" : "0");
  await expect(page.getByTestId("apartment-stale")).toBeVisible();
  await page.getByTestId("assess-apartment").click();
  await expect(page.getByTestId("move-in-total")).toHaveText("€1,300.00");
  await expect(page.getByTestId("apartment-stale")).toHaveCount(0);
});

test("unknown utilities stay unknown and invalid rent receives focus", async ({page}) => {
  await budget(page);
  await page.getByTestId("assess-apartment").click();
  await expect(page.locator("#apartment-rent")).toBeFocused();
  await page.locator("#apartment-rent").fill("650");
  await page.getByTestId("assess-apartment").click();
  await expect(page.getByTestId("summer-total")).toHaveText("Unknown");
  await expect(page.getByTestId("winter-total")).toHaveText("Unknown");
  await expect(page.getByText("Utility costs are still missing", {exact: true})).toBeVisible();
});

test("editing income invalidates the apartment assessment and preserves entered costs", async ({page}) => {
  await budget(page);
  await costs(page);
  await page.locator("#planner-net-income").fill("2200");
  await expect(page.getByTestId("assess-apartment")).toBeDisabled();
  await expect(page.getByTestId("apartment-stale")).toBeVisible();
  await page.locator("form").first().locator('button[type="submit"]').click();
  await expect(page.getByTestId("assess-apartment")).toBeEnabled();
  await expect(page.locator("#apartment-rent")).toHaveValue("650");
  await page.getByTestId("assess-apartment").click();
  await expect(page.getByTestId("winter-remainder")).toHaveText("€350.00");
});

test("map loads only on request, synchronizes platforms and survives address clearing", async ({page}) => {
  let tileRequests = 0;
  await page.route("https://tiles.openfreemap.org/**", route => {
    tileRequests++;
    return route.fulfill({json: {version: 8, sources: {}, layers: [{id: "background", type: "background", paint: {"background-color": "#e7eee7"}}]}});
  });
  await page.route("**/api/v1/transit/nearby**", route => route.fulfill({json: nearby}));
  await budget(page);
  await address(page);
  await expect(page.getByText("Bus 16", {exact: true})).toBeVisible();
  expect(tileRequests).toBe(0);
  await page.getByRole("button", {name: "Show map", exact: true}).click();
  await expect(page.getByTestId("transit-map").locator("canvas")).toBeVisible();
  await expect(page.getByTestId("transit-map").getByRole("button", {name: "Marja, 52 m", exact: true})).toBeVisible();
  await page.getByTestId("location-context").getByRole("button", {name: /Marja 52 m Stop ID/}).click();
  await expect(page.getByTestId("transit-map").getByRole("button", {name: "Marja, 52 m", exact: true})).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("map-unavailable")).toHaveCount(0);
  await page.getByRole("button", {name: "Clear selected address"}).click();
  await expect(page.getByTestId("location-context")).toHaveCount(0);
});

test("transport and tile failure preserve the usable budget and allow retry", async ({page}) => {
  let calls = 0;
  await page.route("**/api/v1/transit/nearby**", route => route.fulfill(++calls === 1 ? {status: 503, json: {}} : {json: {...nearby, feed: {...nearby.feed, freshness: "stale"}}}));
  await page.route("https://tiles.openfreemap.org/**", route => route.abort());
  await budget(page);
  await costs(page);
  await address(page);
  await expect(page.getByTestId("transit-unavailable")).toBeVisible();
  await expect(page.getByTestId("summer-total")).toHaveText("€750.00");
  await page.getByRole("button", {name: "Retry transport"}).click();
  await expect(page.getByTestId("transit-freshness")).toBeVisible();
  await page.getByRole("button", {name: "Show map", exact: true}).click();
  await expect(page.getByTestId("map-unavailable")).toBeVisible({timeout: 15_000});
  await expect(page.getByText("Bus 16", {exact: true})).toBeVisible();
});

for (const [locale, messages] of Object.entries({en, et, ru})) {
  test(`apartment scenario is translated and accessible on mobile (${locale})`, async ({page}) => {
    await page.setViewportSize({width: 390, height: 844});
    await budget(page, locale);
    await costs(page);
    await expect(page.getByRole("heading", {name: messages.apartment.title})).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/(?:apartment|transit|home\.transparency)\.[a-z]/);
    const accessibility = await new AxeBuilder({page}).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(accessibility.violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
