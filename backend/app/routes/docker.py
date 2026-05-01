"""Docker container monitor routes — REST + log-streaming WebSocket."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from app import docker_mon as dm
from app.auth import User, get_current_user, get_current_user_ws

logger = logging.getLogger("beacon.routes.docker")

router = APIRouter(prefix="/api/docker", tags=["docker"])
ws_router = APIRouter(tags=["docker-ws"])

_ID_OR_NAME_PATTERN = r"^[a-zA-Z0-9_.\-]+$"
_ID_OR_NAME_RE = re.compile(_ID_OR_NAME_PATTERN)


def _validated_id(
    container_id: Annotated[str, Path(pattern=_ID_OR_NAME_PATTERN, max_length=128)],
) -> str:
    if not _ID_OR_NAME_RE.match(container_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid container id/name")
    return container_id


class ContainerActionIn(BaseModel):
    action: Literal["start", "stop", "restart", "pause", "unpause", "kill"]


@router.get("/projects")
async def list_projects(
    _user: Annotated[User, Depends(get_current_user)],
    all: bool = Query(True, description="Include stopped containers"),
) -> dict:
    """Containers grouped by docker-compose project label. Each entry has
    name, container_count, running_count, and the full container list."""
    try:
        return dm.list_containers_grouped(all=all)
    except dm.DockerMonError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.get("/containers")
async def list_containers(
    _user: Annotated[User, Depends(get_current_user)],
    all: bool = Query(False, description="Include stopped containers when true"),
) -> list[dict]:
    """Return a compact list of containers (running by default)."""
    try:
        return dm.list_containers(all=all)
    except dm.DockerMonError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.get("/containers/{container_id}")
async def get_container(
    _user: Annotated[User, Depends(get_current_user)],
    container_id: Annotated[str, Depends(_validated_id)],
) -> dict:
    """Return full detail for a single container."""
    try:
        return dm.get_container(container_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except dm.DockerMonError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e


@router.get("/containers/{container_id}/stats")
async def get_container_stats(
    _user: Annotated[User, Depends(get_current_user)],
    container_id: Annotated[str, Depends(_validated_id)],
) -> dict:
    """Return a single sample of container resource stats."""
    try:
        return dm.get_container_stats(container_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except dm.DockerMonError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e


@router.post("/containers/{container_id}/action")
async def post_container_action(
    _user: Annotated[User, Depends(get_current_user)],
    payload: ContainerActionIn,
    container_id: Annotated[str, Depends(_validated_id)],
) -> dict:
    """Run a lifecycle action on a container."""
    try:
        return dm.container_action(container_id, payload.action)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except dm.DockerMonError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@ws_router.websocket("/ws/docker/logs/{container_id}")
async def ws_docker_logs(
    websocket: WebSocket,
    container_id: str,
) -> None:
    """Stream container logs in real time as JSON frames.

    Each frame: ``{"type": "log", "line": str, "ts": float}``. The frame
    ``{"type": "error", "message": str}`` is sent on error before close.
    """
    await get_current_user_ws(websocket)

    if not _ID_OR_NAME_RE.match(container_id or ""):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        tail = int(websocket.query_params.get("tail") or 200)
    except (TypeError, ValueError):
        tail = 200
    follow_param = (websocket.query_params.get("follow") or "true").lower()
    follow = follow_param not in ("0", "false", "no")

    await websocket.accept()

    async def _send(payload: dict) -> None:
        with contextlib.suppress(Exception):
            await websocket.send_json(payload)

    try:
        try:
            agen = dm.stream_logs(container_id, tail=tail, follow=follow)
        except (dm.DockerMonError, ValueError) as e:
            await _send({"type": "error", "message": str(e)})
            return

        try:
            async for line in agen:
                await _send({"type": "log", "line": line, "ts": time.time()})
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("docker log stream failed")
            await _send({"type": "error", "message": f"{type(e).__name__}: {e}"[:500]})
        finally:
            close_fn = getattr(agen, "aclose", None)
            if close_fn is not None:
                with contextlib.suppress(Exception):
                    await close_fn()
    except WebSocketDisconnect:
        return
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()
