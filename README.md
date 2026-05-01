# Beacon

**AI-Native Linux Server Admin Console.** A self-hosted web console that combines real-time monitoring, security auditing, and an AI agent that can inspect and fix Linux server issues with explicit human approval. Built for Synapse Innovation Hack 2026.

> **Security note.** Beacon runs a privileged container with full host access. Only run it on a Linux server you own and intend to administer. Anyone who can reach `https://<host>:443` with the admin credentials has root on this host.

## Quick start

```bash
cp .env.example .env
# Edit .env — see comments inside. Important:
#   - Generate ADMIN_PASS_HASH:
#       docker run --rm caddy:2.8-alpine caddy hash-password --plaintext "yourpass"
#     Then DOUBLE every `$` in the output before pasting (Compose treats single `$` as expansion).
#   - Generate BACKEND_BEARER_TOKEN:
#       openssl rand -hex 32

docker compose up -d --build
# Open https://localhost, accept the self-signed cert, log in.
```

## What it does

- Live system metrics (CPU, memory, disk, network, top processes) — Netdata-style
- Systemd service inventory + start/stop/restart with confirmation
- Cron job management (list/create/edit/delete; run scripts on demand)
- Security audits (SSH config, users, permissions, packages) with apply-fix
- Log tail + search across `/var/log`
- AI chat agent (Groq + LangGraph) that calls the same tools the dashboard uses
- Confirmation gate before any destructive action — enforced by the agent graph, not by trust in the LLM

## Architecture

```
Browser ─https─▶ Caddy (443, tls internal, basic_auth)
                  ├─ static SPA  (React + Vite + Tailwind)
                  └─ /api/* /ws/* ─▶ FastAPI (uvicorn)
                                       ├─ LangGraph agent ─▶ Groq API
                                       └─ tools: psutil, pystemd, python-crontab,
                                                /host/* reads, nsenter --target 1 -- (writes)
```

The backend container runs `--privileged --pid=host --network=host` with `/:/host:rw` and `/run/dbus:/run/dbus` bind-mounts. Mutating commands use `nsenter --target 1` to execute in the host's namespaces.

## Tech stack

- **Backend**: Python 3.11, FastAPI, uvicorn, LangGraph, langchain-groq, psutil, pystemd, python-crontab, aiosqlite, SQLite
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, shadcn-style primitives, TanStack Query, Recharts, react-markdown
- **Reverse proxy / TLS**: Caddy 2.8 with `tls internal` (local CA, self-signed cert)
- **Distribution**: docker-compose, single host

## Status

Hackathon WIP — see `PROGRESS.md` for phase status.

## License

TBD
