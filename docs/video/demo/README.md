# Automated demo runner

Drives a clean Chromium window through the 91-second walkthrough that pairs
with the `voiceover.mp3` narration. No timing skill required — Playwright
clicks/types at exact intervals.

## One-time setup

Already done if you ran the install: `playwright` is in `node_modules/`,
Chromium is downloaded.

## Run a demo session

```bash
cd /home/lefka/Home2/Personal-Projects/hackathons/project
node docs/video/demo/demo.js
```

The script:

1. Opens Chromium maximised at `https://localhost:8443/login`.
2. Pre-fills `admin / beaconadmin`.
3. **Pauses** — the terminal waits for you to press Enter.
4. Switch to your screen recorder, start recording, then come back and
   press Enter.
5. The script clicks/types through the demo over ~91 seconds.
6. Stops with a "STOP RECORDING NOW" message in the terminal.

## What happens in the 91 seconds

| t | action |
|---|---|
| 0:00 | Click Sign In → land on Dashboard (live metrics start updating) |
| 0:20 | Click System (per-core CPU bars, sensors, listening ports) |
| 0:30 | Click Audit, then Run Full Audit |
| 0:46 | Open chat, send "audit my ssh and tell me the most severe issue" |
| 0:58 | Send "create a linux user named demo with sudo + password + ssh key", click Allow on the confirmation card |
| 0:73–0:90 | Quick tour: Firewall → Updates → Docker → Permissions |
| 0:91 | Stop |

## Tunables (env vars)

```bash
MONITSHARK_URL=https://localhost:8443    # if you changed the port
MONITSHARK_USER=admin
MONITSHARK_PASS=beaconadmin
START_DELAY_MS=0   # extra grace after pressing Enter before Sign In click
```

## After recording

```bash
docs/video/combine.sh /path/to/your-recording.mp4
# → produces docs/video/final.mp4
```

Upload `final.mp4` to YouTube unlisted, paste URL into Devpost.
