# MonitShark — Synapse Innovation Hack 2026 Submission

The 7 Devpost sections, ready to paste.

---

## 1. Project Title and Description

**MonitShark — AI-native Linux server admin console.**

MonitShark is a self-hosted web application that runs in Docker on a Linux server and gives administrators a single, live, AI-augmented control plane: real-time monitoring, security auditing, user / firewall / cron / script management, Docker observation, and a chat agent that performs operations on the host with explicit human approval.

It is Cockpit + Netdata + Dozzle + a sysadmin copilot, in one box, accessed at `https://<your-host>/`.

---

## 2. Problem Statement

Three real, common problems converge:

1. **The expertise gap**. Linux server hardening, package patching, firewall management, and cron orchestration are tasks every team needs but only senior engineers do confidently. The smaller the team, the wider the gap. Misconfiguration is the #1 cause of breaches at this tier (Verizon DBIR consistently bears this out).
2. **Tool fragmentation**. Cockpit shows you state but doesn't reason about it. Netdata shows metrics but doesn't act. Dozzle shows Docker logs in isolation. UFW is a CLI. Apt-listchanges is email. Sysadmins context-switch across 10 tools to do one job.
3. **AI agents that talk vs. agents that act**. Most "AI assistants" can describe what an admin should do; very few can do it safely on a real host with proper auditability and consent.

MonitShark addresses all three: one console, AI that calls real tools on the real host, and a confirmation gate enforced in the agent's state machine — not in trust.

---

## 3. Solution Overview

A single Docker-Compose stack with three services: a React+Tailwind SPA, a Python FastAPI + LangGraph backend, and Caddy as a `tls internal` reverse proxy. The backend container runs `--privileged --pid=host` with the host root bind-mounted, so it can read `/proc`, `/sys`, `/etc`, `/var/log` directly and execute mutating commands in the host's namespaces via `nsenter --target 1`.

The agent is the differentiator: 51 LangChain tools wrap the same Python modules the REST API uses (psutil, pystemd, python-crontab, the docker SDK, ufw/apt/dnf shell-outs, etc.). The LangGraph state machine has a planner node (Groq `llama-3.3-70b-versatile`) and a tool_exec node. **Destructive tools — 21 of the 51 — fire `langgraph.types.interrupt`** when called, pausing the graph, surfacing a `confirm_request` frame to the React chat drawer, blocking on the user's `confirm` reply, and resuming via `Command(resume={"decisions": {...}})`. The confirmation gate is in the graph topology, not a bypassable wrapper around the LLM.

11 frontend pages (Dashboard, System, Services, Docker, Cron, Scripts, Audit, Firewall, Updates, Permissions, Logs) cover the same surface manually with React Query + axios + WebSocket hooks. Auth is JWT (HS256, users.yml + bcrypt). Configuration is two yaml files (`port.yml`, `users.yml`) + a `.env` — admin drops them in, `docker compose up`, done.

---

## 4. Working Prototype

- **Repository**: <github URL>
- **Run instructions** (single command after editing `.env`):

  ```bash
  ./start.sh
  ```

  Open `https://localhost/`, accept the self-signed cert, log in (bootstrap password printed in `docker compose logs backend` on first run).

- **Demo video**: <YouTube URL — see `docs/demo-script.md` for the 90-second walkthrough script>

- **Verified end-to-end on Ubuntu 24.04**: 24/24 endpoint smoke tests pass; confirmation gate verified with both deny and approve paths; agent successfully calls inspection tools (`get_metrics`, `list_services`, `audit_ssh`, `run_full_audit`, `list_processes`, etc.) and surfaces real findings (e.g., "Unexpected SUID-root binary: pppd"); WebSocket metrics streams at 1Hz; Docker log WebSocket streams live with multiplex header stripping.

---

## 5. Technical Details

**Backend** — Python 3.11, FastAPI, uvicorn, LangGraph 0.2.50, langchain-groq, psutil, pystemd (with subprocess+jc fallback), python-crontab, aiosqlite, PyJWT, passlib[bcrypt], docker SDK, distro.

**Frontend** — React 18, Vite, TypeScript (strict), Tailwind CSS, shadcn/ui-style primitives (16 of them), TanStack Query, Recharts, axios with bearer interceptor, react-markdown + remark-gfm + rehype-highlight, sonner, react-router-dom, lucide-react icons.

**Reverse proxy / TLS** — Caddy 2.8 with `tls internal` (Caddy's local CA generates and rotates a self-signed cert; first boot auto-saves it under a named volume).

**Agent state machine** — `START → planner → router → {tool_exec | END}`; `tool_exec → planner` (loop). On destructive tool calls, `tool_exec` calls `interrupt({"pending_ops": [...]})`, the WS handler emits a `confirm_request` frame, blocks on the matching `confirm` frame, and resumes the graph with `Command(resume={"decisions": {tool_call_id: "approve" | "deny"}})`. The MemorySaver checkpointer keys per-thread state so users can have parallel conversations.

**Safety invariants**:
- The function `app/util/sh.run` is the only path that imports `subprocess`. A unit test (`test_no_raw_subprocess.py`) walks the source tree and fails CI if any other module imports it.
- Every shell-out uses `shell=False`, list-form args, an explicit timeout, and rejects shell metachars unless `trust_args=True` (used only for fixed enum subcommand tokens).
- Path allowlists for log files, scripts, file browser, and cron paths. All paths resolve through `Path.resolve()` then `is_relative_to(allowed_root)`.
- Pydantic + regex validation on every user-controlled tool input.
- 21 destructive tools all run through the confirmation gate; the planner system prompt explicitly tells the LLM that denied results are final ("don't retry").

**Distribution** — single Docker-Compose stack; bootstraps `config/` from `config.example/` on first run; one-time admin password generated and printed if `users.yml`'s admin entry has an empty `password_hash`. `start.sh` handles `.env` generation (`openssl rand -hex 32` for `JWT_SECRET`) and reads `port.yml` to override Caddy ports without editing compose.

---

## 6. Use Case and Impact

**Primary**: small teams and indie operators who run their own Linux servers — homelabs, side-project SaaS, internal tools, edu / research lab boxes. They need cockpit-class manageability without enterprise complexity.

**Educational**: the audit pages surface *why* a setting is risky (each finding includes a description with the threat model, not just the violation). Students hardening their first VPS get a guided tour.

**Operational**: ops engineers who routinely SSH into a box, run `apt list --upgradable | grep -i security`, then `systemctl restart something`, then check `/var/log/auth.log` get the same workflow with one chat message: *"are there security updates? if so, apply them and confirm sshd is healthy."*

**Impact metrics for the admin role**:
- Cuts a typical multi-step hardening pass from minutes to seconds.
- Surfaces 4 categories of audit findings (SSH config, user accounts, permissions, packages) automatically; ~20 specific checks today, designed to be extended.
- 51 actions exposed via natural language — without sacrificing safety, because each destructive action requires a click.

---

## 7. Team Information

**Spyros Lefkaditis** — solo. Computer science student. AI solutions engineer; strong in cybersecurity. Built and shipped MonitShark end-to-end during the Synapse Innovation Hack 2026 window.

Contributions: project conception, architecture, every line of design choice, end-to-end implementation across backend (Python/FastAPI/LangGraph), frontend (React/TypeScript/Tailwind), DevOps (Docker, Caddy, JWT auth), agent integration (Groq + LangGraph confirmation gate), security model, testing, and documentation.

---

## Optional sections

- **Slides**: not provided — the running app is the deck.
- **UI/UX designs**: see `https://localhost/` once the stack is up. Light + dark themes via `data-theme` attribute, amber accent, JetBrains Mono for tabular numerics.
- **Future scalability** — see Roadmap in README.md.
