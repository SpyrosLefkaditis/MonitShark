"""Cron CRUD + ad hoc script run. Bearer-auth on every endpoint."""
from __future__ import annotations

import re
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, status

from app import cron as cron_svc
from app.auth import User, get_current_user
from app.schemas import (
    CronCreateIn,
    CronEntry,
    CronRunIn,
    CronRunOut,
    CronUpdateIn,
)
from app.util.paths import PathRejected
from app.util.sh import CommandRejected

router = APIRouter(prefix="/api/cron", tags=["cron"])

_ID_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}::\d+$")


def _check_id(entry_id: str) -> str:
    decoded = unquote(entry_id)
    if not _ID_RE.match(decoded):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"invalid cron id: {entry_id!r}")
    return decoded


@router.get("", response_model=list[CronEntry])
async def list_entries(
    _: Annotated[User, Depends(get_current_user)],
    user: str | None = None,
) -> list[CronEntry]:
    try:
        return cron_svc.list_all(user=user)
    except cron_svc.CronError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.post("", response_model=CronEntry, status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: CronCreateIn,
    _: Annotated[User, Depends(get_current_user)],
) -> CronEntry:
    try:
        return cron_svc.create(payload)
    except cron_svc.CronError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except (ValueError, KeyError) as e:
        # python-crontab raises ValueError on invalid schedule strings.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid cron entry: {e}") from e


@router.put("/{entry_id}", response_model=CronEntry)
async def update_entry(
    entry_id: str,
    payload: CronUpdateIn,
    _: Annotated[User, Depends(get_current_user)],
) -> CronEntry:
    decoded = _check_id(entry_id)
    try:
        return cron_svc.update(decoded, payload)
    except cron_svc.CronError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except (ValueError, KeyError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid update: {e}") from e


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: str,
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    decoded = _check_id(entry_id)
    try:
        cron_svc.delete(decoded)
    except cron_svc.CronError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    return {"ok": True}


@router.post("/run", response_model=CronRunOut)
async def run_entry(
    payload: CronRunIn,
    _: Annotated[User, Depends(get_current_user)],
) -> CronRunOut:
    try:
        return cron_svc.run_script(payload)
    except PathRejected as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"script not allowed: {e}") from e
    except CommandRejected as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"command rejected: {e}") from e
