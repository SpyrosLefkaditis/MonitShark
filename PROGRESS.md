# Beacon — implementation progress

Tracks `/loop` phase completion. Source of truth for "what's the next phase to run."

## Phases

- [x] **Phase 0** — Repo bootstrap & one-command compose — *2026-05-01*
- [ ] **Phase 1** — Frontend layout, theme, design system
- [ ] **Phase 2** — Backend read-only system surface + REST
- [ ] **Phase 3** — WebSocket metrics + alerts engine
- [ ] **Phase 4** — Frontend pages with REST data
- [ ] **Phase 5** — Live metrics over WebSocket
- [ ] **Phase 6** — Agent skeleton with read-only tools
- [ ] **Phase 7** — Confirmation gate + write tools
- [ ] **Phase 8** — Polish, tests, writeup, demo video

## Phase 0 — completed 2026-05-01

**Files created** (root + backend + frontend skeleton):

- Root: `.gitignore`, `.dockerignore`, `README.md`, `docker-compose.yml`, `Caddyfile`, `.env.example`
- Backend: `Dockerfile`, `entrypoint.sh`, `requirements.txt`, `pyproject.toml`, `.dockerignore`, `app/__init__.py`, `app/main.py` (FastAPI with `/api/health`), `tests/__init__.py`
- Frontend: `Dockerfile`, `.dockerignore`, `package.json`, `tsconfig.json`, `tsconfig.node.json`, `vite.config.ts`, `tailwind.config.ts`, `postcss.config.js`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/styles/globals.css`

**Static validation passed:**
- `docker compose config` → exit 0 (only warnings about unset env vars, expected)
- `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` → "Valid configuration"
- `python3 -m ast` parse of `backend/app/main.py` → OK

**Runtime verification (deferred to user environment):** the user runs `docker compose up -d --build` on their target host with a real `.env`; they then verify with the curl/browser checks listed in the plan §12.

## Next phase

Phase 1 — extends `frontend/src/styles/globals.css` (already has full HSL vars in Phase 0), then adds the theme provider, Button + Card primitives, and the rest of the shadcn primitives needed for the layout. Builds RootLayout + Sidebar + Topbar + ThemeToggle and the 5 route stubs.
