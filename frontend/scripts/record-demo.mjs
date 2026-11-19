/*
 * Drives the Vulniverse editor through a full GCVE workflow, for a demo
 * video (e.g. the README's animation) or a manual end-to-end check:
 *
 *   new GCVE record -> Patch2Vuln analysis of a patch -> reserve a GCVE ID
 *   on Vulnerability-Lookup -> apply the generated fields -> edit a field
 *   picked in the tree -> save -> preview -> publish to Vulnerability-Lookup
 *
 * Needs a running Vulniverse in local mode (no login), with the
 * Patch2Vuln panel configured and CNA credentials for Vulnerability-Lookup.
 * It changes real data: it creates a record, reserves a GCVE ID and
 * publishes it.
 *
 * Usage, from frontend/:
 *   PATCH_URL=https://github.com/owner/repo/commit/<sha> node scripts/record-demo.mjs
 *
 * Options (environment variables):
 *   PATCH_URL   the commit to analyse (required)
 *   BASE        the editor's address        (default http://localhost:5173)
 *   NEW_TITLE   the title typed in the edit step
 *   THEME       light or dark               (default light)
 *   WIDTH, HEIGHT  window size; below about 1440 px wide the editor's
 *               header buttons wrap onto two lines  (default 1600 x 900)
 *   VIDEO_DIR   record a video (.webm) into this folder; with ffmpeg
 *               installed, a successful run also makes the animated WebP
 *               for the README from it, without the Patch2Vuln wait
 *   WEBP        where to write that WebP
 *               (default VIDEO_DIR/editor-demo-<THEME>.webp)
 *   HEADED=1    show the browser window
 *   CHROMIUM    path to a Chromium binary, if Playwright's own isn't
 *               installed (`npx playwright install chromium` installs it)
 */

import { execFileSync } from "node:child_process";

import { chromium } from "@playwright/test";

const PATCH_URL = process.env.PATCH_URL;
const BASE = process.env.BASE ?? "http://localhost:5173";
const NEW_TITLE = process.env.NEW_TITLE ?? "Heap overflow in the image parser";
const THEME = process.env.THEME === "dark" ? "dark" : "light";
const VIDEO_DIR = process.env.VIDEO_DIR;
const SIZE = { width: Number(process.env.WIDTH ?? 1600), height: Number(process.env.HEIGHT ?? 900) };

if (!PATCH_URL) {
  console.error("Set PATCH_URL to a commit URL, e.g. https://github.com/owner/repo/commit/<sha>");
  process.exit(1);
}

// Patch2Vuln runs a language model: give it time.
const PATCH2VULN_TIMEOUT_MS = 15 * 60_000;
// After anything changes on screen: long enough to read it in the video.
const READ_MS = 1500;

const browser = await chromium.launch({
  headless: !process.env.HEADED,
  executablePath: process.env.CHROMIUM,
});
const context = await browser.newContext({
  viewport: SIZE,
  colorScheme: THEME,
  ...(VIDEO_DIR ? { recordVideo: { dir: VIDEO_DIR, size: SIZE } } : {}),
});

// Videos don't show the system pointer: draw one that follows the mouse.
await context.addInitScript(() => {
  addEventListener("DOMContentLoaded", () => {
    const dot = document.createElement("div");
    dot.style.cssText = "position:fixed;z-index:2147483647;pointer-events:none;width:18px;height:18px;"
      + "margin:-9px 0 0 -9px;border-radius:50%;background:rgba(220,60,60,.55);"
      + "box-shadow:0 0 0 2px #fff;transition:transform .1s;left:-50px;top:-50px";
    document.body.append(dot);
    addEventListener("mousemove", (event) => {
      dot.style.left = `${event.clientX}px`;
      dot.style.top = `${event.clientY}px`;
    }, true);
    addEventListener("mousedown", () => { dot.style.transform = "scale(.7)"; }, true);
    addEventListener("mouseup", () => { dot.style.transform = ""; }, true);
  });
});

const page = await context.newPage();
// The video starts with the page: step times tell where to cut it, e.g.
// the minutes Patch2Vuln spends analysing.
const started = Date.now();
// The Patch2Vuln wait, in seconds of video, to cut out afterwards.
const wait = { from: 0, to: 0 };
page.setDefaultTimeout(30_000);

/** Seconds since the video started. */
function elapsed() {
  return (Date.now() - started) / 1000;
}

function step(text) {
  const seconds = Math.round(elapsed());
  const time = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  console.log(`[${time}] ${text}`);
}

/** Moves the pointer visibly to the element, then clicks it. */
async function click(locator) {
  await scrollTo(locator);
  const box = await locator.boundingBox();
  if (box) {
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 20 });
    await page.waitForTimeout(150);
  }
  await locator.click();
}

/**
 * Wheel-scrolls in small steps until the element is in view, like a person
 * would; Playwright's own scrolling jumps there in one frame.
 */
async function scrollTo(locator) {
  const margin = 80;
  let pointerPlaced = false;

  for (let tries = 0; tries < 80; tries++) {
    const box = await locator.boundingBox();
    if (!box) {
      break;
    }
    const below = box.y + box.height - (SIZE.height - margin);
    const above = margin - box.y;
    if (below <= 0 && above <= 0) {
      return;
    }
    if (!pointerPlaced) {
      await page.mouse.move(SIZE.width * 0.6, SIZE.height * 0.6, { steps: 20 });
      pointerPlaced = true;
    }
    await page.mouse.wheel(0, below > 0 ? Math.min(50, below) : -Math.min(50, above));
    await page.waitForTimeout(40);
  }

  // The wheel can't reach it (e.g. another scrolling box): jump after all.
  await locator.scrollIntoViewIfNeeded();
}

/** Scrolls the section under the pointer smoothly, `distance` px down. */
async function scroll(distance) {
  await page.mouse.move(SIZE.width * 0.6, SIZE.height * 0.6, { steps: 20 });
  for (let done = 0; done < distance; done += 50) {
    await page.mouse.wheel(0, 50);
    await page.waitForTimeout(40);
  }
}

async function pause(ms = READ_MS) {
  await page.waitForTimeout(ms);
}

/** Opens a section or panel from the editor's sidebar. */
async function open(name) {
  await click(page.getByRole("button", { name, exact: true }).first());
  await pause(800);
}

/** Fails with the panel's own message if one of `failures` shows up first. */
async function waitForText(success, failures, timeout) {
  const outcome = await Promise.race([
    page.getByText(success).first().waitFor({ timeout }).then(() => "ok"),
    ...failures.map((failure) =>
      page.getByText(failure).first().waitFor({ timeout }).then(() => failure)),
  ]);
  if (outcome !== "ok") {
    throw new Error(`Stopped: the editor shows "${outcome}"`);
  }
}

try {
  step("New GCVE record");
  await page.goto(`${BASE}/editor/new`);
  await pause(800);
  await click(page.getByRole("button", { name: "Create as GCVE" }));
  await pause();

  step(`Patch2Vuln: analyse ${PATCH_URL}`);
  await open("Patch2Vuln");
  const patchField = page.getByPlaceholder("https://github.com/owner/repo/commit/...");
  await click(patchField);
  await patchField.pressSequentially(PATCH_URL, { delay: 25 });
  await pause(600);
  await click(page.getByRole("button", { name: "Analyze patches" }));
  await pause();

  step("Vulnerability-Lookup: reserve a GCVE ID (saves the record first)");
  await open("Vulnerability-Lookup");
  await click(page.getByRole("button", { name: "Reserve a GCVE ID" }));
  // Its first real save moves a new record to its own address, which opens
  // a fresh editor (on the Editor section): reopen the panel there.
  await page.waitForURL(/\/editor\/\d+$/, { timeout: 60_000 });
  await pause(800);
  await open("Vulnerability-Lookup");
  await waitForText("Reserved, not published yet", ["Reserving didn't complete", "isn't configured"], 60_000);
  await pause();

  step("Patch2Vuln: wait for the analysis, then apply all generated fields");
  await open("Patch2Vuln");
  // The cut keeps 2 s of "Analyzing..." on each side of the wait.
  wait.from = elapsed() + 2;
  await waitForText("Analysis completed successfully.", ["Analysis failed.", "Analysis canceled."], PATCH2VULN_TIMEOUT_MS);
  wait.to = elapsed() - 2;
  step("Patch2Vuln: analysis done");
  await pause();
  // Every field starts selected.
  await click(page.getByRole("button", { name: "Apply selected fields" }));
  await pause();

  step("Tree: find the title and open it in the editor");
  await open("Tree");
  const search = page.getByLabel("Search the tree");
  await click(search);
  await search.pressSequentially("Title", { delay: 80 });
  await search.press("Enter");
  await pause();
  await click(page.locator("text.record-graph-label", { hasText: /^Title\b/ }).first());
  await pause();

  step(`Edit the title: "${NEW_TITLE}"`);
  // Opening a field from the tree focuses it in the editor.
  const field = page.locator("textarea:focus, input:focus");
  await field.waitFor();
  await field.selectText();
  await field.pressSequentially(NEW_TITLE, { delay: 60 });
  await pause();

  step("Save");
  await click(page.getByRole("button", { name: "Save", exact: true }));
  await page.getByText("Unsaved changes").waitFor({ state: "detached" });
  await pause();

  step("Preview");
  await open("Preview");
  await pause(1000);
  await scroll(1200);
  await pause();
  await scroll(1200);
  await pause();

  step("Vulnerability-Lookup: publish");
  await open("Vulnerability-Lookup");
  await click(page.getByRole("button", { name: "Publish to Vulnerability-Lookup" }));
  await waitForText(
    "Published on Vulnerability-Lookup",
    ["Publishing didn't complete", "Fix the marked fields before publishing."],
    60_000,
  );
  await pause(3000);

  step("Done");
} catch (error) {
  await page.screenshot({ path: "record-demo-failure.png", fullPage: true });
  console.error(`${error.message}\nScreenshot of the moment: record-demo-failure.png`);
  process.exitCode = 1;
} finally {
  const video = page.video();
  await context.close(); // writes the video
  await browser.close();
  if (video) {
    const path = await video.path();
    console.log(`Video: ${path}`);
    if (!process.exitCode) {
      makeWebp(path);
    }
  }
}

/**
 * The animated WebP for the README, in one ffmpeg step: without the
 * Patch2Vuln wait, at 12 frames per second (enough for a UI, and small),
 * 1200 px wide (sharp when shown smaller), looping.
 */
function makeWebp(path) {
  const output = process.env.WEBP ?? path.replace(/[^/]+\.webm$/, `editor-demo-${THEME}.webp`);
  const cut = wait.to > wait.from
    ? `select='not(between(t,${wait.from.toFixed(2)},${wait.to.toFixed(2)}))',setpts=N/FRAME_RATE/TB,`
    : "";

  console.log("Making the WebP…");
  try {
    execFileSync("ffmpeg", [
      "-loglevel", "error", "-y", "-i", path,
      "-vf", `${cut}fps=12,scale=1200:-1:flags=lanczos`,
      "-c:v", "libwebp_anim", "-lossless", "0", "-quality", "75",
      "-compression_level", "4", "-loop", "0", "-an", output,
    ], { stdio: "inherit" });
    console.log(`WebP${cut ? ` (Patch2Vuln wait of ${Math.round(wait.to - wait.from)} s cut)` : ""}: ${output}`);
  } catch {
    console.log(`ffmpeg failed or isn't installed. The wait to cut: ${wait.from.toFixed(1)}–${wait.to.toFixed(1)} s.`);
  }
}
