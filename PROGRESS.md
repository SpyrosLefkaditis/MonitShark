# Beacon — implementation progress

Tracks `/loop` phase completion. Source of truth for "what's the next phase to run."

## Phases

- [x] **Phase 0** — Repo bootstrap & one-command compose — *2026-05-01*
- [x] **Phase 1** — Frontend layout, theme, design system — *2026-05-01*
- [x] **Phase 2** — Backend read-only system surface + REST — *2026-05-01*
- [x] **Phase 3** — WebSocket metrics + alerts engine — *2026-05-01* (folded into Phase 2; verified live)
- [ ] **Phase 4** — Frontend pages with REST data — *in progress (agent)*
- [ ] **Phase 5** — Live metrics over WebSocket — *in progress (agent)*
- [x] **Phase 6** — Agent skeleton with read-only tools — *2026-05-01*
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

## Phase 1 — completed 2026-05-01

**Files added** (frontend):

- `src/lib/utils.ts` — `cn()` helper.
- `src/theme/provider.tsx` — `<ThemeProvider>` + `useTheme()` (light/dark, persisted in localStorage, follows system on first load).
- `src/components/ui/*` (16 primitives) — Button, Card (+ Header/Title/Description/Content/Footer), Input, Textarea, Label, Badge, Skeleton, Separator, Dialog (+ Header/Footer/Title/Description/Overlay/Trigger/Close/Portal), Sheet (right-drawer for chat, with cva-driven `side` variants), Tooltip (+ Provider), ScrollArea (+ ScrollBar), Select (full Radix surface), Switch, Tabs (List/Trigger/Content), Sonner Toaster (theme-integrated wrapper).
- `src/components/layout/*` — RootLayout (sidebar + topbar + main + chat-drawer-Sheet), Sidebar (5 NavLinks with lucide icons + brand), Topbar (page title + AlertsBadge + "Ask Beacon" button), ThemeToggle (sun/moon button), AlertsBadge (stub returning count=0; Phase 3 wires to /api/alerts).
- `src/pages/*` — DashboardPage, ServicesPage, CronPage, AuditPage, LogsPage, NotFoundPage. Each is a placeholder Card describing what lands in later phases.
- `src/App.tsx` — composes ThemeProvider → QueryClientProvider → TooltipProvider → BrowserRouter → Routes (RootLayout wraps all routes) + Toaster.

**Verification:**
- Frontend Docker image builds clean (`tsc -b` + `vite build`). Bundle: 330 kB JS / 24 kB CSS (105 kB gzipped JS).
- No TypeScript errors with `strict: true`.
- All 16 primitives import from packages already pinned in `package.json` (no missing deps).

## Next phase

Phase 2 — Backend read-only system surface + REST. Adds `app/config.py`, `app/auth.py`, `app/db.py`, `app/schemas.py`, `app/util/{sh,nsenter,paths}.py`, `app/metrics.py` (psutil), `app/services.py` (pystemd + nsenter fallback), `app/cron.py` (python-crontab), `app/logs.py` (tail/search), `app/audits/{ssh,users,permissions,packages}.py`, and the route handlers under `app/routes/`. Bearer-token auth dep on every protected route.
