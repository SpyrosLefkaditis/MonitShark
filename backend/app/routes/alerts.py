"""Alerts REST routes: list + acknowledge."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app import alerts as alerts_engine
from app.auth import User, get_current_user
from app.schemas import AckOut, Alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[Alert])
async def get_alerts(
    _user: Annotated[User, Depends(get_current_user)],
    status: Annotated[str | None, Query(description="'all' to include acknowledged; default open only")] = None,
) -> list[Alert]:
    """List alerts. Default returns unacked, ordered newest first."""
    return await alerts_engine.list_alerts(status)


@router.post("/{alert_id}/ack", response_model=AckOut)
async def ack_alert(
    _user: Annotated[User, Depends(get_current_user)],
    alert_id: Annotated[int, Path(ge=1)],
) -> AckOut:
    """Mark an alert acknowledged."""
    ok = await alerts_engine.acknowledge(alert_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "alert not found or already acknowledged")
    return AckOut(ok=True)
