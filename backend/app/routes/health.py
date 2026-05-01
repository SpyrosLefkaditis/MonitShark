"""Health + readiness endpoints. /api/health is unauthenticated by design (used
by Caddy + Docker healthchecks). /api/ready is also unauth — judges expect to
hit it without a token to verify the box is up."""
from __future__ import annotations

import time

from fastapi import APIRouter

from app.config import settings
from app.schemas import HealthOut

router = APIRouter(prefix="/api", tags=["health"])

VERSION = "0.2.0"
START_TIME = time.monotonic()


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(ok=True, version=VERSION, uptime_s=round(time.monotonic() - START_TIME, 2))


@router.get("/ready")
async def ready() -> dict:
    return {
        "ok": True,
        "groq_key_present": bool(settings.groq_api_key and not settings.groq_api_key.startswith("gsk_replace")),
        "jwt_secret_set": bool(settings.jwt_secret and settings.jwt_secret != "dev-only-replace-me-please"),
    }
