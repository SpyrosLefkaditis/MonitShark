"""Beacon FastAPI application — wires routers, lifespan, background tasks."""
from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app import alerts as alerts_mod
from app import metrics as metrics_mod
from app.config import settings
from app.db import db
from app.routes import (
    alerts as alerts_routes,
    audits as audits_routes,
    auth as auth_routes,
    chat as chat_routes,
    cron as cron_routes,
    docker as docker_routes,
    firewall as firewall_routes,
    health as health_routes,
    logs as logs_routes,
    metrics as metrics_routes,
    permissions as permissions_routes,
    scripts as scripts_routes,
    services as services_routes,
    updates as updates_routes,
    users as users_routes,
)
# `system` route module may not exist yet (still being written) — best-effort import.
try:
    from app.routes import system as system_routes  # type: ignore[no-redef]
except ImportError:
    system_routes = None

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("beacon")


async def _metrics_push_loop() -> None:
    """1Hz background snapshot push for the rolling buffer used by /ws/metrics."""
    while True:
        try:
            metrics_mod.push()
        except Exception:
            logger.exception("metrics push failed")
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            return


async def _alerts_loop() -> None:
    """Wraps the alerts poller; restarts on unexpected exit."""
    while True:
        try:
            await alerts_mod.poller_task()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("alerts poller crashed; restarting in 5s")
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                return


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await db.connect()
    push_task = asyncio.create_task(_metrics_push_loop(), name="metrics-push")
    alerts_task = asyncio.create_task(_alerts_loop(), name="alerts-poller")
    logger.info("Beacon backend ready (data_dir=%s, config_dir=%s)", settings.data_dir, settings.config_dir)
    try:
        yield
    finally:
        for t in (push_task, alerts_task):
            t.cancel()
        for t in (push_task, alerts_task):
            with contextlib.suppress(asyncio.CancelledError):
                await t
        await db.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Beacon",
        version="0.2.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # REST
    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(metrics_routes.router)
    app.include_router(services_routes.router)
    app.include_router(cron_routes.router)
    app.include_router(logs_routes.router)
    app.include_router(audits_routes.router)
    app.include_router(alerts_routes.router)
    app.include_router(scripts_routes.router)
    app.include_router(permissions_routes.router)
    app.include_router(users_routes.router)
    app.include_router(firewall_routes.router)
    app.include_router(updates_routes.router)
    app.include_router(docker_routes.router)
    if system_routes is not None and hasattr(system_routes, "router"):
        app.include_router(system_routes.router)
    app.include_router(chat_routes.router)

    # WebSockets
    app.include_router(metrics_routes.ws_router)
    app.include_router(chat_routes.ws_router)
    if hasattr(docker_routes, "ws_router"):
        app.include_router(docker_routes.ws_router)

    return app


app = create_app()
