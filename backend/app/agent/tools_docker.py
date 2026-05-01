"""@tool wrappers around app.docker_mon for the LangGraph agent.

Read-only tools execute inline. ``DESTRUCTIVE_NAMES`` lists actions that the
graph's confirmation node must gate before they run.
"""
from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import tool

from app import docker_mon as dm


def _err(e: Exception) -> dict[str, Any]:
    return {"ok": False, "error": f"{type(e).__name__}: {e}"}


@tool
def docker_list_containers(all: bool = False) -> list[dict]:
    """List Docker containers running on the host.

    By default returns only running containers; pass ``all=True`` to also
    include stopped/exited containers. Each entry includes id, short_id,
    name, image, status, state, created timestamp, port bindings, labels,
    and (when present) the healthcheck status."""
    try:
        return dm.list_containers(all=bool(all))
    except (dm.DockerMonError, ValueError):
        return []


@tool
def docker_get_container(container_id: str) -> dict:
    """Return full detail for one container — image, command, ports, mounts,
    network mode + per-network IPs, restart policy, labels, and a filtered
    view of the container's environment (sensitive variables are redacted).

    ``container_id`` may be the full id, the short id (>=4 hex chars), or
    the container name."""
    try:
        return dm.get_container(container_id)
    except (dm.DockerMonError, ValueError) as e:
        return _err(e)


@tool
def docker_get_container_stats(container_id: str) -> dict:
    """Return a single sample of resource stats for the given container:
    CPU%, memory used/limit/percent, total network rx/tx bytes since start,
    cumulative block I/O read/write bytes. ``container_id`` accepts id or name."""
    try:
        return dm.get_container_stats(container_id)
    except (dm.DockerMonError, ValueError) as e:
        return _err(e)


@tool
def docker_list_projects(all: bool = True) -> dict:
    """List Docker containers grouped by their docker-compose project label.
    Each project entry has name, container_count, running_count, and a list
    of containers. Use this for a project-aware overview."""
    try:
        return dm.list_containers_grouped(all=bool(all))
    except (dm.DockerMonError, ValueError) as e:
        return _err(e)


@tool
def docker_container_action(
    container_id: str,
    action: Literal["start", "stop", "restart", "pause", "unpause", "kill"],
) -> dict:
    """Run a lifecycle action on a Docker container. Destructive — must pass
    the confirmation gate. ``action`` is one of start, stop, restart, pause,
    unpause, kill."""
    try:
        return dm.container_action(container_id, action)
    except (dm.DockerMonError, ValueError) as e:
        return _err(e)


TOOLS = [
    docker_list_containers,
    docker_list_projects,
    docker_get_container,
    docker_get_container_stats,
    docker_container_action,
]

DESTRUCTIVE_NAMES = {
    "docker_container_action",
}
