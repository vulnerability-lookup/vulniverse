/*
 * Screenshots of the editor's views of one record, in light and dark,
 * for the README's gallery: the form, the record tree, the preview, the
 * list of unsaved changes, the JSON comparison and the quality check.
 *
 * Needs a running Vulniverse in local mode (no login). Without RECORD,
 * it first saves scripts/demo-record.json (a made-up advisory) as a new
 * draft and uses that. The edits for the change views are never saved:
 * each view starts from a fresh load. From frontend/:
 *   node scripts/take-screenshots.mjs
 *
 * Options (environment variables):
 *   RECORD    an existing record to show instead of the demo record
 *   BASE      the editor's address     (default http://localhost:5173)
 *   OUT       where the .webp files go (default ../docs/docs/images/screenshots)
 *   CHROMIUM  path to a Chromium binary, if Playwright's own isn't installed
 */

import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { chromium } from "@playwright/test";

const BASE = process.env.BASE ?? "http://localhost:5173";
const OUT = process.env.OUT ?? "../docs/docs/images/screenshots";
const SIZE = { width: 1600, height: 1000 };

const pngs = mkdtempSync(join(tmpdir(), "vulniverse-shots-"));
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM });

/** Opens a section or panel from the editor's sidebar. */
async function open(page, name) {
  await page.getByRole("button", { name, exact: true }).first().click();
}

/** Saves the demo record as a new draft; its id. */
async function createDemoRecord() {
  const page = await browser.newPage({ viewport: SIZE });
  page.setDefaultTimeout(15_000);
  const json = readFileSync(new URL("./demo-record.json", import.meta.url), "utf8");

  await page.goto(`${BASE}/editor/new`);
  await page.getByRole("button", { name: "Create as GCVE" }).click();
  await open(page, "Advanced JSON");
  await page.locator("textarea.json-source").fill(json);
  await page.getByRole("button", { name: "Apply JSON" }).click();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await page.waitForURL(/\/editor\/\d+$/);

  const id = page.url().split("/").pop();
  await page.close();
  return id;
}

/**
 * Two unsaved edits, written for demo-record.json: a reworded title and
 * a removed problem type (its second one).
 */
async function edit(page) {
  await page.getByRole("button", { name: "Summary" }).click();
  await page.getByLabel("Title", { exact: true }).first()
    .fill("FlowIntel deadline notifications disclose private case and task titles");
  await page.getByRole("button", { name: "Classification" }).click();
  await page.locator(".card[data-path$='problemTypes.1'] > .card-header").getByRole("button", { name: "Remove" }).click();
}

/** The views, each: get there from a freshly loaded record. */
const VIEWS = {
  editor: async (page) => {
    await page.getByRole("button", { name: "Affected products" }).click();
    const versions = page.locator("[data-path$='affected.0.versions']");
    // Open the first version, unless it already is (a single one opens by itself).
    const toggle = versions.locator(".card-header button").first();
    if ((await toggle.innerText()).includes("▸")) {
      await toggle.click();
    }
    // The versions at the top, below the editor's header.
    await versions.evaluate((element) => element.scrollIntoView({ block: "start" }));
    await page.mouse.wheel(0, -24);
  },
  tree: async (page) => {
    await open(page, "Tree");
  },
  preview: async (page) => {
    await open(page, "Preview");
  },
  changes: async (page) => {
    await edit(page);
    await page.locator(".editor-unsaved-toggle").click();
  },
  "json-changes": async (page) => {
    await edit(page);
    await open(page, "Advanced JSON");
    await page.getByRole("button", { name: /^Changes/ }).click();
  },
  quality: async (page) => {
    await open(page, "Record Quality");
  },
};

try {
  const record = process.env.RECORD || await createDemoRecord();
  console.log(`Record ${record}`);

  for (const theme of ["light", "dark"]) {
    const page = await browser.newPage({ viewport: SIZE, colorScheme: theme });
    page.setDefaultTimeout(15_000);

    for (const [name, show] of Object.entries(VIEWS)) {
      await page.goto(`${BASE}/editor/${encodeURIComponent(record)}`);
      await page.getByRole("button", { name: "Tree", exact: true }).first().waitFor();
      await show(page);
      await page.waitForTimeout(1500);

      // The editor only, not the app's own top bar around it.
      const box = await page.locator(".vulniverse-editor").first().boundingBox();
      const top = Math.max(box.y, 0);
      const png = join(pngs, `${name}-${theme}.png`);
      await page.screenshot({
        path: png,
        clip: { x: box.x, y: top, width: box.width, height: SIZE.height - top - 16 },
      });

      const webp = join(OUT, `${name}-${theme}.webp`);
      execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-i", png, "-c:v", "libwebp", "-quality", "85", webp]);
      console.log(webp);
    }

    await page.close();
  }
} finally {
  await browser.close();
  rmSync(pngs, { recursive: true, force: true });
}
