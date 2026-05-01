"""systemd service routes: list, detail, action."""
from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.auth import User, get_current_user
from app.schemas import ServiceActionIn, ServiceActionOut, ServiceItem
from app.services import ServiceError, action, detail, list_units

router = APIRouter(prefix="/api/services", tags=["services"])

_NAME_RE = re.compile(r"^[a-zA-Z0-9_@.\-:]+$")
_NAME_PATTERN = r"^[a-zA-Z0-9_@.\-:]+$"


def _validated_name(
    name: Annotated[str, Path(pattern=_NAME_PATTERN, max_length=256)],
) -> str:
    if not _NAME_RE.match(name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid unit name")
    return name


@router.get("", response_model=list[ServiceItem])
async def list_services(
    _user: Annotated[User, Depends(get_current_user)],
    filter: str | None = Query(None, description="systemctl --state= filter, e.g. 'active'"),
) -> list[ServiceItem]:
    """List `.service` units, optionally filtered by state."""
    try:
        return list_units(state=filter)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except ServiceError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.get("/{name}")
async def get_service(
    _user: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Depends(_validated_name)],
) -> dict:
    """Return detailed status + recent journal for a single unit."""
    try:
        return detail(name)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except ServiceError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.post("/{name}/action", response_model=ServiceActionOut)
async def post_service_action(
    _user: Annotated[User, Depends(get_current_user)],
    payload: ServiceActionIn,
    name: Annotated[str, Depends(_validated_name)],
) -> ServiceActionOut:
    """Run start/stop/restart/reload on the named unit."""
    try:
        return action(name, payload.action)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except ServiceError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
