"""System update routes. Bearer auth on every endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app import updates as upd
from app.auth import User, get_current_user

router = APIRouter(prefix="/api/updates", tags=["updates"])


@router.get("")
async def list_updates(_: Annotated[User, Depends(get_current_user)]) -> dict:
    """Return ``{package_manager, total, security_count, packages}``."""
    pm = upd.detect_pm()
    pkgs = upd.list_upgradable()
    return {
        "package_manager": pm,
        "total": len(pkgs),
        "security_count": sum(1 for p in pkgs if p.get("is_security")),
        "packages": pkgs,
    }


@router.post("/apply-security")
async def apply_security(_: Annotated[User, Depends(get_current_user)]) -> dict:
    """Apply only security-flagged updates. Long-running."""
    return upd.upgrade_security_only()


@router.post("/apply-all")
async def apply_all(_: Annotated[User, Depends(get_current_user)]) -> dict:
    """Apply every pending update. Long-running."""
    return upd.upgrade_all()
