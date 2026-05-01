// MonitShark demo runner — drives a clean Chromium and records the session
// itself. No screen recorder needed. Pairs with docs/video/voiceover.mp3.
//
// USAGE:
//   node docs/video/demo/demo.js
//
//   1. Stack must be up (docker compose ps shows backend + caddy healthy).
//   2. Run the command. Chromium opens at /login.
//   3. The script drives the entire demo for ~91 seconds and writes a
//      WebM recording to docs/video/recording.webm.
//   4. After it finishes:  docs/video/combine.sh docs/video/recording.webm
//      → docs/video/final.mp4
//
// Env knobs:
//   MONITSHARK_URL   default https://localhost:8443
//   MONITSHARK_USER  default admin
//   MONITSHARK_PASS  default beaconadmin

const { chromium } = require("playwright");
const path = require("node:path");
const fs = require("node:fs");

const URL = process.env.MONITSHARK_URL || "https://localhost:8443";
const USER = process.env.MONITSHARK_USER || "admin";
const PASS = process.env.MONITSHARK_PASS || "beaconadmin";

const VIDEO_DIR = path.resolve(__dirname, "..", ".video-tmp");
const FINAL_PATH = path.resolve(__dirname, "..", "recording.webm");

const CHAT_MSG_1 = "audit my ssh and tell me the most severe issue";
const CHAT_MSG_2 =
  "create a linux user named demo with sudo, password tempBeacon42, " +
  "and ssh key ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDfakekey99 test@beacon";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(VIDEO_DIR, { recursive: true });
  // Wipe any old recordings in the temp dir.
  for (const f of fs.readdirSync(VIDEO_DIR)) {
    if (f.endsWith(".webm")) fs.unlinkSync(path.join(VIDEO_DIR, f));
  }

  console.log("Launching Chromium…");
  const browser = await chromium.launch({
    headless: false,
    args: [
      "--window-size=1920,1080",
      "--window-position=0,0",
      "--disable-infobars",
      "--disable-extensions",
      "--no-default-browser-check",
      "--no-first-run",
      "--ignore-certificate-errors",
    ],
  });

  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
    deviceScaleFactor: 1,
    colorScheme: "dark",
    recordVideo: {
      dir: VIDEO_DIR,
      size: { width: 1920, height: 1080 },
    },
  });
  const page = await ctx.newPage();

  console.log("Loading /login…");
  await page.goto(`${URL}/login`, { waitUntil: "networkidle" });
  // Brief blank-frame buffer so the recording's first second is clean.
  await sleep(1000);

  console.log();
  console.log("=================================================");
  console.log("  Demo starts in 3 seconds. The browser is on the");
  console.log("  login page; the script will type credentials,");
  console.log("  click through every page, drive the chat, and");
  console.log("  approve the confirmation gate. Walk away — it'll");
  console.log("  take ~91 seconds.");
  console.log("=================================================");
  for (let i = 3; i > 0; i--) {
    process.stdout.write(`  ${i}… `);
    await sleep(1000);
  }
  console.log("GO\n");

  // ───── 0:00 — type credentials, click Sign In ─────
  // The login form preloads the username with "admin", so we triple-click
  // to select the existing text — typing then REPLACES it instead of
  // appending and producing "adminadmin".
  console.log("[0:00] type creds + sign in");
  const usernameField = page.locator('input[id="username"]');
  await usernameField.click({ clickCount: 3 });
  await sleep(150);
  await usernameField.type(USER, { delay: 80 });
  await sleep(300);
  const passwordField = page.locator('input[id="password"]');
  await passwordField.click({ clickCount: 3 });
  await sleep(120);
  await passwordField.type(PASS, { delay: 70 });
  await sleep(500);
  await page.click('button[type="submit"]');
  await sleep(18500); // dashboard loads, live metrics visible — ends ~0:21

  // ───── 0:20 — System page ─────
  console.log("[0:20] System");
  await page.click('a[href="/system"]');
  await sleep(10000); // ends ~0:30

  // ───── 0:30 — Audit + Run Full Audit ─────
  console.log("[0:30] Audit");
  await page.click('a[href="/audit"]');
  await sleep(2000);
  try {
    await page.getByRole("button", { name: /Run full audit/i }).click({ timeout: 4000 });
  } catch {
    await page.locator("button:has-text('Run full audit')").first().click();
  }
  await sleep(13500); // ends ~0:46 (findings rendered)

  // ───── 0:46 — chat msg #1 ─────
  console.log("[0:46] chat: msg #1");
  await page.getByRole("button", { name: /Ask MonitShark/i }).click();
  await sleep(800);
  const textarea = page.locator('[role="dialog"] textarea').last();
  await textarea.click();
  await textarea.type(CHAT_MSG_1, { delay: 18 });
  await sleep(200);
  await textarea.press("Enter");
  await sleep(11000); // ends ~0:58

  // ───── 0:58 — chat msg #2 + click Allow ─────
  console.log("[0:58] chat: msg #2 + Allow");
  await textarea.click();
  await textarea.type(CHAT_MSG_2, { delay: 14 });
  await sleep(200);
  await textarea.press("Enter");
  try {
    await page.getByRole("button", { name: /^Allow$/i }).click({ timeout: 12000 });
  } catch {
    console.log("   (Allow button never appeared — agent may have rate-limited; continuing tour)");
  }
  await sleep(7000); // ends ~0:73

  // ───── 0:73 — quick tour ─────
  console.log("[0:73] tour");
  await page.click('a[href="/firewall"]');     await sleep(4500);
  await page.click('a[href="/updates"]');      await sleep(4500);
  await page.click('a[href="/docker"]');       await sleep(4500);
  await page.click('a[href="/permissions"]');  await sleep(4000);

  console.log("[0:91] done — closing browser, saving recording");

  // Closing the context flushes the video to disk.
  const video = page.video();
  await ctx.close();
  await browser.close();

  if (video) {
    const src = await video.path();
    if (src) {
      fs.copyFileSync(src, FINAL_PATH);
      try { fs.unlinkSync(src); } catch {}
      console.log();
      console.log("=================================================");
      console.log(`  Saved:  ${FINAL_PATH}`);
      console.log();
      console.log("  Stitch with intro + outro + voiceover:");
      console.log(`     docs/video/combine.sh ${FINAL_PATH}`);
      console.log("=================================================");
    }
  } else {
    console.log("(no video found — check Playwright logs above)");
  }
})();
