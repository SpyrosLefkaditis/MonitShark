from __future__ import annotations

import time

from fastapi import FastAPI

START_TIME = time.monotonic()
VERSION = "0.1.0"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Beacon",
        version=VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "ok": True,
            "version": VERSION,
            "uptime_s": round(time.monotonic() - START_TIME, 2),
        }

    return app


app = create_app()
