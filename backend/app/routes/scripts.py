"""User-script CRUD + run + install-as-service + schedule-via-cron."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from app import scripts as scripts_svc
from app.auth import User, get_current_user
from app.util.paths import PathRejected
from app.util.sh import CommandRejected

router = APIRouter(prefix="/api/scripts", tags=["scripts"])

_NAME_PATTERN = r"^[a-zA-Z0-9_-]{1,64}$"


def _name_param(
    name: Annotated[str, Path(pattern=_NAME_PATTERN, max_length=64)],
) -> str:
    return name


class ScriptSaveIn(BaseModel):
    content: str = Field(..., max_length=2_000_000)
    make_executable: bool = True


class ScriptRunIn(BaseModel):
    args: list[str] = Field(default_factory=list)
    timeout_s: int = 60


class ScriptInstallServiceIn(BaseModel):
    service_name: str
    description: str = ""
    restart: str = "no"


class ScriptScheduleIn(BaseModel):
    schedule: str
    user: str = "root"


def _wrap_script_error(e: Exception) -> HTTPException:
    if isinstance(e, scripts_svc.ScriptError):
        return HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    if isinstance(e, PathRejected):
        return HTTPException(status.HTTP_400_BAD_REQUEST, f"path not allowed: {e}")
    if isinstance(e, CommandRejected):
        return HTTPException(status.HTTP_400_BAD_REQUEST, f"command rejected: {e}")
    if isinstance(e, FileNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, repr(e))


@router.get("")
async def list_scripts_route(
    _: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    return scripts_svc.list_scripts()


@router.get("/{name}")
async def get_script_route(
    _: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Depends(_name_param)],
) -> dict[str, Any]:
    try:
        return scripts_svc.get_script(name)
    except Exception as e:
        raise _wrap_script_error(e) from e


@router.put("/{name}")
async def save_script_route(
    payload: ScriptSaveIn,
    _: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Depends(_name_param)],
) -> dict[str, Any]:
    try:
        return scripts_svc.save_script(
            name=name,
            content=payload.content,
            make_executable=payload.make_executable,
        )
    except Exception as e:
        raise _wrap_script_error(e) from e


@router.delete("/{name}")
async def delete_script_route(
    _: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Depends(_name_param)],
) -> dict[str, Any]:
    try:
        return scripts_svc.delete_script(name)
    except Exception as e:
        raise _wrap_script_error(e) from e


@router.post("/{name}/run")
async def run_script_route(
    payload: ScriptRunIn,
    _: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Depends(_name_param)],
) -> dict[str, Any]:
    try:
        return scripts_svc.run_script(
            name=name,
            args=payload.args,
            timeout_s=payload.timeout_s,
        )
    except Exception as e:
        raise _wrap_script_error(e) from e


@router.post("/{name}/install-service")
async def install_service_route(
    payload: ScriptInstallServiceIn,
    _: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Depends(_name_param)],
) -> dict[str, Any]:
    try:
        return scripts_svc.install_as_service(
            script_name=name,
            service_name=payload.service_name,
            description=payload.description,
            restart=payload.restart,
        )
    except Exception as e:
        raise _wrap_script_error(e) from e


@router.post("/{name}/schedule")
async def schedule_route(
    payload: ScriptScheduleIn,
    _: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Depends(_name_param)],
) -> dict[str, Any]:
    try:
        return scripts_svc.schedule_via_cron(
            script_name=name,
            schedule=payload.schedule,
            user=payload.user,
        )
    except Exception as e:
        raise _wrap_script_error(e) from e
