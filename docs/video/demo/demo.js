// MonitShark demo runner — drives a clean Chromium window through the
// 91-second walkthrough that pairs with docs/video/voiceover.mp3.
//
// USAGE:
//   1. Stack must be up (docker compose ps shows backend + caddy healthy).
//   2. Run:  node docs/video/demo/demo.js
//   3. A maximised Chromium window opens and prefills the login form.
//   4. The script PAUSES — start your screen recorder NOW, then hit Enter
//      in this terminal to begin.
//   5. The script clicks/types through the demo over ~91 seconds.
//   6. Stop your recording when the script prints "STOP RECORDING NOW".
//
// Knobs (env):
//   MONITSHARK_URL   default https://localhost:8443
//   MONITSHARK_USER  default admin
//   MONITSHARK_PASS  default beaconadmin
//   START_DELAY_MS   default 0   — extra delay after Enter before clicking Sign In

const { chromium } = require("playwright");
const readline = require("node:readline");

const URL = process.env.MONITSHARK_URL || "https://localhost:8443";
const USER = process.env.MONITSHARK_USER || "admin";
const PASS = process.env.MONITSHARK_PASS || "beaconadmin";
const START_DELAY = parseInt(process.env.START_DELAY_MS || "0", 10);

// Two pre-typed prompts for the chat.
const CHAT_MSG_1 = "audit my ssh and tell me the most severe issue";
const CHAT_MSG_2 =
  "create a linux user named demo with sudo, password tempBeacon42, " +
  "and ssh key ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDfakekey99 test@beacon";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function waitForEnter(prompt) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(prompt, () => {
      rl.close();
      resolve();
    });
  });
}

(async () => {
  console.log(`Opening Chromium against ${URL} …`);

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
  });
  const page = await ctx.newPage();

  // Land on /login and prefill creds (everything except the click).
  await page.goto(`${URL}/login`, { waitUntil: "networkidle" });
  await page.fill('input[id="username"]', USER);
  await page.fill('input[id="password"]', PASS);
  await sleep(500);

  console.log();
  console.log("=================================================");
  console.log(" Login form ready. Browser is positioned at /login");
  console.log(" with credentials prefilled.");
  console.log();
  console.log(" 1. Switch to your screen recorder.");
  console.log(" 2. Start recording.");
  console.log(" 3. Come back here and press ENTER to begin.");
  console.log("=================================================");
  console.log();
  await waitForEnter("Press ENTER when recording is rolling… ");

  if (START_DELAY > 0) await sleep(START_DELAY);

  // ───────── 0:00 — sign in ─────────
  console.log("[0:00] sign in");
  await page.click('button[type="submit"]');
  // Login → dashboard transition. Wait long enough for the dashboard to be
  // visible and the live metrics chart to start moving.
  await page.waitForURL(/\/$/, { timeout: 15000 }).catch(() => {});
  await sleep(20000); // 0:00 → 0:20  (includes login redirect ~2s)

  // ───────── 0:20 — System page ─────────
  console.log("[0:20] System");
  await page.click('a[href="/system"]');
  await sleep(10000); // 0:20 → 0:30

  // ───────── 0:30 — Audit + Run Full Audit ─────────
  console.log("[0:30] Audit");
  await page.click('a[href="/audit"]');
  await sleep(2000);
  await page.getByRole("button", { name: /Run full audit/i }).click()
    .catch(async () => {
      // Fallback selector.
      await page.locator("button:has-text('Run full audit')").click();
    });
  await sleep(14000); // 0:32 → 0:46  (audit + findings render)

  // ───────── 0:46 — open chat, send msg #1 ─────────
  console.log("[0:46] Chat: msg #1 (audit my SSH)");
  await page.getByRole("button", { name: /Ask MonitShark/i }).click();
  await sleep(1000);
  // Chat textarea is inside the right-side Sheet drawer.
  const textarea = page.locator('[role="dialog"] textarea, [data-radix-scroll-area-viewport] ~ * textarea, textarea').last();
  await textarea.fill(CHAT_MSG_1);
  await sleep(300);
  await textarea.press("Enter");
  await sleep(11000); // 0:47 → 0:58  (agent thinks + streams response)

  // ───────── 0:58 — chat msg #2 + Allow ─────────
  console.log("[0:58] Chat: msg #2 (create user) + click Allow");
  await textarea.fill(CHAT_MSG_2);
  await sleep(300);
  await textarea.press("Enter");
  // Wait for the confirmation card to appear; click Allow when it shows.
  await page.getByRole("button", { name: /^Allow$/i }).click({ timeout: 12000 })
    .catch(() => console.log("  (Allow button didn't appear — agent may be rate-limited; continuing)"));
  await sleep(8000); // 0:58 + ~7s click wait + 8s = ends ~0:73

  // ───────── 0:73 — quick sidebar tour ─────────
  console.log("[0:73] tour: Firewall");
  await page.click('a[href="/firewall"]');     await sleep(4000);
  console.log("[0:77] tour: Updates");
  await page.click('a[href="/updates"]');      await sleep(4000);
  console.log("[0:81] tour: Docker");
  await page.click('a[href="/docker"]');       await sleep(4000);
  console.log("[0:85] tour: Permissions");
  await page.click('a[href="/permissions"]');  await sleep(5000);

  console.log();
  console.log("=================================================");
  console.log("  STOP RECORDING NOW.   (~91s elapsed)");
  console.log("=================================================");
  console.log();
  console.log(" Save the recording, then run:");
  console.log("   docs/video/combine.sh path/to/your-recording.mp4");
  console.log();

  await sleep(2000);
  await browser.close();
})();
