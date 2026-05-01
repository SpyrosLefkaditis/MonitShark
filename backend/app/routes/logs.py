"""Log sources, tail, and search. Bearer-auth on every endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import logs as logs_svc
from app.auth import User, get_current_user
from app.schemas import LogSearchIn, LogSearchOut, LogSourcesOut, LogTailOut
from app.util.paths import PathRejected

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/sources", response_model=LogSourcesOut)
async def sources(
    _: Annotated[User, Depends(get_current_user)],
) -> LogSourcesOut:
    return LogSourcesOut(paths=logs_svc.list_sources())


@router.get("", response_model=LogTailOut)
async def tail(
    _: Annotated[User, Depends(get_current_user)],
    path: str = Query(..., description="Display path, e.g. /var/log/auth.log"),
    lines: int = Query(200, ge=1, le=2000),
) -> LogTailOut:
    try:
        return logs_svc.tail(path, lines)
    except PathRejected as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"path not allowed: {e}") from e
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.post("/search", response_model=LogSearchOut)
async def search(
    payload: LogSearchIn,
    _: Annotated[User, Depends(get_current_user)],
) -> LogSearchOut:
    try:
        return logs_svc.search(payload)
    except PathRejected as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"path not allowed: {e}") from e
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
