"""File permission inspector / editor over curated browseable roots."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app import permissions as perms_svc
from app.auth import User, get_current_user
from app.util.paths import PathRejected
from app.util.sh import CommandRejected

router = APIRouter(prefix="/api/fs", tags=["permissions"])


class ChmodIn(BaseModel):
    path: str
    mode_octal: str


class ChownIn(BaseModel):
    path: str
    owner: str | None = None
    group: str | None = None


def _wrap(e: Exception) -> HTTPException:
    if isinstance(e, PathRejected):
        return HTTPException(status.HTTP_400_BAD_REQUEST, f"path not allowed: {e}")
    if isinstance(e, CommandRejected):
        return HTTPException(status.HTTP_400_BAD_REQUEST, f"command rejected: {e}")
    if isinstance(e, FileNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    if isinstance(e, ValueError):
        return HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, repr(e))


@router.get("/list")
async def list_route(
    _: Annotated[User, Depends(get_current_user)],
    path: str = Query(..., description="Display path, e.g. /etc"),
) -> dict[str, Any]:
    try:
        result = perms_svc.list_dir(path)
        result["roots"] = perms_svc.browseable_roots()
        return result
    except Exception as e:
        raise _wrap(e) from e


@router.get("/info")
async def info_route(
    _: Annotated[User, Depends(get_current_user)],
    path: str = Query(..., description="Display path, e.g. /etc/ssh/sshd_config"),
) -> dict[str, Any]:
    try:
        return perms_svc.get_file_info(path)
    except Exception as e:
        raise _wrap(e) from e


@router.post("/chmod")
async def chmod_route(
    payload: ChmodIn,
    _: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        return perms_svc.chmod_path(path=payload.path, mode_octal=payload.mode_octal)
    except Exception as e:
        raise _wrap(e) from e


@router.post("/chown")
async def chown_route(
    payload: ChownIn,
    _: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    try:
        return perms_svc.chown_path(
            path=payload.path,
            owner=payload.owner,
            group=payload.group,
        )
    except Exception as e:
        raise _wrap(e) from e
