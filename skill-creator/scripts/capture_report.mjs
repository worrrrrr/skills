import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";
const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error("Usage: node capture_report.mjs <report.html> <screenshot.png>");
  process.exit(3);
}
const report = resolve(input), screenshot = resolve(output);
await mkdir(dirname(screenshot), { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(report).href, { waitUntil: "load" });
  await page.screenshot({ path: screenshot, fullPage: true });
  console.log("Screenshot captured: " + screenshot);
} finally { await browser.close(); }
