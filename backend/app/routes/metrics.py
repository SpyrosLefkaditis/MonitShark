"""Metrics REST + WebSocket routes.

REST: `/api/metrics` (current snapshot), `/api/metrics/history` (rolling buffer).
WS:   `/ws/metrics?token=...` — 1Hz fan-out of fresh snapshots.
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app import metrics
from app.auth import User, get_current_user, get_current_user_ws
from app.schemas import MetricsSnapshot

router = APIRouter(prefix="/api", tags=["metrics"])
ws_router = APIRouter(tags=["metrics-ws"])


@router.get("/metrics", response_model=MetricsSnapshot)
async def get_metrics(
    _user: Annotated[User, Depends(get_current_user)],
) -> MetricsSnapshot:
    """Return a fresh metrics snapshot."""
    return metrics.snapshot()


@router.get("/metrics/history", response_model=list[MetricsSnapshot])
async def get_metrics_history(
    _user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(60, ge=1, le=600),
) -> list[MetricsSnapshot]:
    """Return up to `limit` most-recent snapshots from the rolling buffer."""
    return metrics.history(limit)


@ws_router.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket) -> None:
    """1Hz metrics fan-out. Validates JWT before accepting the upgrade."""
    await get_current_user_ws(websocket)
    await websocket.accept()
    try:
        while True:
            snap = metrics.push()
            await websocket.send_json(snap.model_dump())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
