# Beacon

**Self-hosted, AI-native Linux server admin console.** A web app you `docker compose up` on your own machine that gives you live monitoring, security auditing, user/firewall/cron/script management, Docker container observation, and a chat agent that *actually performs operations* on the host with explicit human approval.

> Built for **Synapse Innovation Hack 2026**.
>
> **Trusted-admin tool.** Beacon runs a privileged container with full host access. Only run it on a Linux server you own and intend to administer. Anyone who can reach `https://<host>:443` with the admin credentials has root on this host.

---

## Quick start

```bash
git clone <this repo>
cd project
./start.sh
# 1st run: writes .env from .env.example. Edit it to set GROQ_API_KEY
#          (free key at https://console.groq.com).
# 2nd run: builds + brings up the stack.
./start.sh
# On first launch the backend logs print a one-time bootstrap admin password.
docker compose logs backend | grep -A 3 "bootstrap admin"
```

Open `https://localhost/` (or `:8443` if you set a non-default port via `config/port.yml`), accept the self-signed cert, sign in.

Three config files live under `config/` (auto-created on first boot from `config.example/`):

- `config/port.yml` — HTTP/HTTPS host ports (default 80/443)
- `config/users.yml` — admin accounts (bcrypt-hashed; first boot generates one)
- `.env` — `GROQ_API_KEY`, `JWT_SECRET`, `LOG_LEVEL`, port overrides

---

## What it does

### 11 management surfaces

| Page | Capability |
|---|---|
| **Dashboard** | Live metrics over WebSocket: CPU/mem/disk/network sparklines, 60-frame multi-series chart, top-10 processes, open-alert list. |
| **System** | Kernel, distro, uptime, CPU model. **Per-core CPU bars**. Per-disk I/O rates. Per-NIC throughput (delta-based). **Sensors** (temps, fans, battery). Kernel modules. Listening ports with PID/process. |
| **Services** | All 100+ systemd `.service` units with state. Start / stop / restart / reload (confirmation-gated). |
| **Docker** | Containers list with state badge. Action buttons. Live log streaming over WebSocket (multiplex header stripped). Stats (CPU%/mem/net/blockio). |
| **Cron** | Per-user spool tabs + system crontab. Create / edit / delete entries. Run-now with timeout + stdout capture. |
| **Scripts** | Bash script editor under `/opt/cockpit/scripts/`. Save, run with args, **install as oneshot systemd service**, **schedule via cron**. |
| **Audit** | 4 security audits (SSH, users, permissions, packages). Run-all populates the findings DB. **Apply Fix** for each finding (sshd_config edits, world-writable cleanup, etc.). |
| **Firewall (UFW)** | Status + default policies. Add / delete rules with action + port + proto + source + comment. Enable/disable toggle. |
| **Updates** | Distro-aware (apt/dnf). Security-only updates separately. Pending package list with current/new version. |
| **Permissions** | File browser scoped to `/etc`, `/opt/cockpit`, `/var/log`, `/home`, `/root`. **chmod** (octal + checkbox grid) and **chown** with confirmation. |
| **Logs** | Tail any file under `/var/log`. Regex search. **Ask Beacon to analyze** handoff to chat. |

### The AI agent (Groq + LangGraph)

The right-hand chat drawer. **51 tools** registered: 30 read-only (inspection) and 21 destructive (gated by an explicit confirmation card the user clicks Allow / Deny on).

**Demo prompts:**

- *"What's my CPU and memory at right now?"* → calls `get_metrics` → live numbers.
- *"Run a full security audit and tell me the most severe finding."* → calls `run_full_audit` → ranked findings with evidence.
- *"Create a Linux user named 'spyros' with sudo and SSH key `ssh-ed25519 AAAA…`."* → confirmation card pops up → click Allow → user is created.
- *"Add a firewall rule allowing tcp 8080 from 10.0.0.0/24."* → confirmation card → click Allow → rule added.
- *"Apply all security updates."* → confirmation card → click Allow → host updated.

Confirmation enforcement lives in the LangGraph state machine (`interrupt()` on destructive tool calls), **not** in a wrapper the LLM could bypass.

---

## Architecture

```
Browser ─https─▶ Caddy 2.8 (tls internal, self-signed, port 443)
                  ├─ static SPA  (React 18 + Vite + Tailwind + shadcn/ui)
                  └─ /api/* /ws/* ─▶ FastAPI + uvicorn (bridge net, port 8000)
                                       ├─ JWT auth (HS256, users.yml)
                                       ├─ LangGraph agent ─▶ Groq llama-3.3-70b
                                       │   └─ interrupt() confirmation gate
                                       ├─ aiosqlite (findings, alerts, threads)
                                       └─ tool surface:
                                            psutil + /proc + /sys
                                            pystemd / nsenter -- systemctl
                                            python-crontab over /host/var/spool/cron
                                            ufw / apt / dnf via nsenter
                                            docker SDK over /var/run/docker.sock
                                            useradd / chpasswd / chown via nsenter
```

The backend container runs `--privileged --pid=host` with `/:/host:rw` and `/run/dbus:/run/dbus`. Mutating commands use `nsenter --target 1` to execute in the host's namespaces; reads go directly through the bind-mount. The compose stack is a **single command**: backend, Caddy, frontend-build (one-shot artifact builder).

### Safety / sandboxing

- **One subprocess gate**. `app/util/sh.run` is the only path that calls `subprocess`; a unit test enforces no other module imports it. shell=False; list args only; rejects shell metachars unless explicitly trusted (whitelisted enum-style).
- **Path allowlists**. Log paths under `/var/log`, file browser under 5 fixed roots, scripts only under `/opt/cockpit/scripts`, no arbitrary host paths.
- **Pydantic + regex validation** on every tool input — usernames, service names, schedule strings, package names, container ids — before they reach `nsenter`.
- **Confirmation gate** for the 21 destructive tools, in the LangGraph state graph.
- **JWT auth** issued by `/api/auth/login` against `users.yml` (bcrypt-hashed). All REST + WS endpoints validate. Stateless — no session DB.

---

## Tech stack

- **Backend**: Python 3.11, FastAPI, uvicorn, LangGraph, langchain-groq, psutil, pystemd, python-crontab, aiosqlite, PyJWT, passlib[bcrypt], docker, distro
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, shadcn-style primitives, TanStack Query, Recharts, axios, react-markdown, sonner
- **Reverse proxy / TLS**: Caddy 2.8 with `tls internal` (local CA, self-signed)
- **Agent**: Groq API (`llama-3.3-70b-versatile`, switchable via `GROQ_MODEL` env)
- **Distribution**: docker-compose, single host

---

## Configuration

All three are auto-bootstrapped from `config.example/` on first boot.

### `config/port.yml`

```yaml
ports:
  http: 80
  https: 443
backend:
  bind_host: 127.0.0.1
  bind_port: 8000
```

### `config/users.yml`

```yaml
users:
  - username: admin
    password_hash: ""    # leave empty; entrypoint fills + prints once
    role: admin
```

### `.env`

```
GROQ_API_KEY=gsk_...                         # required
JWT_SECRET=...                               # auto-generated by start.sh
ADMIN_USER=admin                             # legacy, kept for compatibility
HTTPS_PORT=443
HTTP_PORT=80
LOG_LEVEL=info
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## Status

Hackathon WIP. See `PROGRESS.md` for phase status.

End-to-end test against an Ubuntu 24.04 host: 24/24 endpoint checks pass; confirmation gate verified with both deny + approve flows; agent successfully calls `get_metrics`, `list_processes`, `run_full_audit`, `audit_ssh`, etc. against live host state and returns ranked, evidence-backed answers.

---

## Roadmap

- Comprehensive audit expansion (kernel sysctls, mount options, firewall posture, failed-login bursts, CIS benchmark mapping)
- Multi-host fleet management
- Code-splitting the frontend bundle
- An open-ended "agent-driven" audit where the LLM plans checks dynamically
- Custom dashboard layouts

## License

TBD
