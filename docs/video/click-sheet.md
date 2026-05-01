# Click sheet — record this in 7 anchor points (~91 seconds)

**Before you press record:**

1. Stack is up: `docker compose ps` shows backend + caddy healthy.
2. Browser is on `https://localhost:8443/login` — already typed `admin` and the password but **NOT** clicked Sign In yet.
3. Run a quick audit once **beforehand** so the findings table is non-empty when you click Audit during recording (the chat will still rerun it; this just saves a moment).
4. Have these two strings on a sticky-note / clipboard / second tab so you can paste them fast:
   - **chat msg #1** → `audit my ssh and tell me the most severe issue`
   - **chat msg #2** → `create a linux user named demo with sudo, password tempBeacon42, and ssh key ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDfakekey99 test@beacon`
5. Browser zoom = 100%, devtools closed, notifications off, theme = dark.
6. Resolution = 1080p (1920×1080). 30 fps is fine.

---

## The 7 anchors — count seconds in your head

> Tip: tap your finger on the desk once per second. After ~91 you stop.

| at | do this | what's happening |
|---|---|---|
| **0:00** | Click **Sign In** | enter the app |
| **0:05** | (just look at the Dashboard. wave the mouse over a metric card so the sparkline moves) | live metrics |
| **0:18** | Click **System** in the sidebar | per-core CPU, sensors |
| **0:28** | Click **Audit**. Wait ~1 sec, click **Run full audit** | findings populate |
| **0:44** | Click **Ask MonitShark** (top right). Paste **chat msg #1**, press Enter | agent calls audit_ssh, streams answer |
| **0:55** | When the previous answer is done streaming, paste **chat msg #2**, press Enter. *When the amber **Confirmation card** appears, click **Allow*** | agent creates the user |
| **0:73** | Click **Firewall** in sidebar (1.5s). Click **Updates** (1.5s). Click **Docker** (1.5s). Click **Permissions** (1.5s). Then stop on Permissions | quick feature tour |
| **0:91** | **STOP recording** | done |

---

## If you go a bit over or under

Don't worry. Aim for ~91 but anything from 85 to 100 seconds is fine — I'll trim/pad with ffmpeg when stitching. Just **stop on a clean frame** (not mid-click, not mid-typing).

## What if the agent rate-limits mid-recording?

Free-tier Groq has a daily token cap. If you see the friendly "Daily token budget exhausted" message at 0:44, your recording is still useful — most of the value (Dashboard / System / Audit / Firewall / Updates / Docker / Permissions) is non-LLM. Cut the chat segment in editing if needed; we still have a strong demo.
