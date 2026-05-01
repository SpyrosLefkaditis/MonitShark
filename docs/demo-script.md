# MonitShark — 90-second demo video script

**Length target: 90 seconds** (Devpost's optional-but-strongly-recommended demo video has no hard cap, but judges skim. 60-90s is the sweet spot. If the video runs long, cut Section 4 first.)

**Recording setup**:
- 1920×1080, 30 fps, system audio off (or low — judges read).
- OBS or `wf-recorder` on Linux. Record the Chrome window only (not full desktop).
- Stack must be up: `./start.sh` and `docker compose ps` shows backend + caddy healthy.
- Browser at `https://localhost/`, already logged in as admin.
- Pre-populate: run a full audit once so findings are persisted. Have a public SSH key on your clipboard for the create-user moment (use a fresh test key, not your real one — generate via `ssh-keygen -t ed25519 -f /tmp/demo -N ''` then `cat /tmp/demo.pub`).

---

## Beat sheet (90 s total)

### 0:00–0:08 — Title card + framing (8 s)

Plain dark background, title:

> **MonitShark — AI-native Linux server admin console**
> *Synapse Innovation Hack 2026*

Voiceover or text overlay:
> *"Cockpit + Netdata + an AI sysadmin copilot, in one Docker box."*

### 0:08–0:18 — One-command install (10 s)

Cut to a terminal:
```
$ git clone .../beacon
$ cd beacon
$ ./start.sh
```
Brief montage of compose pulling images, then `Browser → https://localhost/`. Show the login page, type the password, hit enter.

> *"One command. Self-hosted. JWT auth. Self-signed TLS via Caddy."*

### 0:18–0:28 — Dashboard (live) (10 s)

Hover the Dashboard. The four metric cards (CPU, Mem, Disk, Net) update visibly — sparklines move. Wave the multi-series chart at the bottom.

> *"Live metrics over WebSocket. Top processes. Open alerts."*

### 0:28–0:36 — System page (8 s)

Click **System** in the sidebar. Show per-core CPU bars, sensors (temps), listening ports.

> *"Per-core CPU. Sensors. Listening ports with the process behind each one."*

### 0:36–0:44 — Audit page (8 s)

Click **Audit** → **Run full audit** button. Findings populate, grouped by severity.

> *"Four security audits — SSH, users, permissions, packages. Findings with evidence."*

### 0:44–0:60 — The agent does the work (16 s) ⭐ MONEY SHOT

Click **Ask MonitShark** (top right). The chat drawer slides open. Type:

> "Audit my SSH config and tell me the most severe issue."

The agent's tool-call card appears: **`audit_ssh_config`**. Result card collapses. Final answer streams:

> *"The most severe finding is `PermitRootLogin yes` (high). [reasoning…]"*

### 0:60–0:80 — Confirmation gate (20 s) ⭐ THE OTHER MONEY SHOT

Same chat. Type:

> "Create a Linux user `demo` with sudo and this SSH key: `<paste from clipboard>`."

Tool-call card: **`create_user`**. Then a **Confirmation card** with amber border slides in:

> *"Create Linux user 'demo' with sudo, password, SSH key — `risk: high`"*
> [Allow] [Deny]

Click **Allow**. Tool-result card shows `{ok: true, ssh_key_installed: true}`. Final reply: *"Done. The user `demo` was created with sudo and your key."*

Cut to a terminal, prove it:
```
$ docker compose exec backend cat /host/etc/passwd | grep demo
demo:x:1001:1001::/home/demo:/bin/bash
```

### 0:80–0:90 — Closing (10 s)

Quick cuts: **Firewall** (UFW rules table) → **Updates** (security updates list) → **Docker** (live container logs scrolling) → **Permissions** (file picker → chmod dialog).

End card:
> **MonitShark. Self-hosted. AI-acted. Human-approved.**
> *github.com/<...>/beacon*

---

## Recording checklist

Before pressing record:
- [ ] Stack is up; `docker compose ps` says healthy on both backend + caddy
- [ ] You're logged into the UI; theme is set (dark looks better on camera)
- [ ] Audits already populated (so the page shows findings instantly, not "Loading…")
- [ ] One previous chat thread cleared, so the chat starts clean
- [ ] A fresh ed25519 SSH key is in your clipboard (use a throwaway test key)
- [ ] Browser zoom 100%, devtools closed
- [ ] Notifications muted, no calendar pop-ups, no Slack/Discord
- [ ] Screen is 1080p exactly
- [ ] Recording: only the browser window, not the full desktop

After recording:
- [ ] Trim to 60-90 s
- [ ] Add captions for spoken parts (judges often watch on mute)
- [ ] Export as 1080p MP4, H.264, ~5 Mbps target
- [ ] Upload to YouTube unlisted; copy the URL into the README and into Devpost
