import { chromium } from "@playwright/test";
import path from "path";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";
const SCREENSHOTS_DIR = path.resolve(__dirname, "../../docs/screenshots");

async function run() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: "light",
  });
  const page = await context.newPage();

  await page.goto(`${BASE_URL}/en`, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "home.png"), fullPage: true });
  console.log("home screenshot saved");

  await page.goto(`${BASE_URL}/en/calculator`, { waitUntil: "networkidle" });
  await page.fill("#gross-monthly-income", "3000");
  await page.selectOption("#pension-pillar-rate", "0.02");
  await page.click("button[type='submit']");
  await page.waitForSelector("[aria-live='polite'] .font-semibold", { timeout: 10000 });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "calculator.png"), fullPage: true });
  console.log("calculator screenshot saved");

  await page.goto(`${BASE_URL}/en/housing`, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "housing.png"), fullPage: true });
  console.log("housing screenshot saved");

  await browser.close();
  console.log("done");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
