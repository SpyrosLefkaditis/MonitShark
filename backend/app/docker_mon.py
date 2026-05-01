"""Docker container monitor.

Wraps the official `docker` Python SDK against the host's docker socket
(bind-mounted at /var/run/docker.sock). The functions defined here are the
shared implementation between the REST/WS routes and the LangGraph agent
tools.

The module is named ``docker_mon`` (not ``docker``) so it does not shadow the
``docker`` SDK package itself.
"""
from __future__ import annotations

import asyncio
import logging
import re
import struct
import time
from typing import Any, AsyncIterator, Iterable

import docker
from docker.errors import APIError, NotFound

logger = logging.getLogger("beacon.docker")

# Container ids are 64-hex; we accept the short form (>=4 chars) too. Names
# follow Docker's naming rules (alnum + ._-). Keep this strict — every
# user-controlled string lands here before the SDK call.
_ID_OR_NAME_RE = re.compile(r"^(?:[a-f0-9]{4,64}|[a-zA-Z0-9_.-]+)$")

# Allowlist of env-var prefixes considered safe to surface in container detail.
# Anything outside the allowlist is replaced with "***" so we do not leak
# tokens, passwords, API keys, etc. into the dashboard.
_SAFE_ENV_PREFIXES: tuple[str, ...] = (
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "LC_",
    "TZ",
    "TERM",
    "PWD",
    "HOSTNAME",
    "NODE_ENV",
    "PYTHONUNBUFFERED",
    "PYTHONDONTWRITEBYTECODE",
    "DEBIAN_FRONTEND",
    "PORT",
    "BIND_HOST",
    "BIND_PORT",
    "LOG_LEVEL",
    "HOST_ROOT",
    "DATA_DIR",
    "CONFIG_DIR",
)


class DockerMonError(RuntimeError):
    """Raised when the Docker daemon refuses or is unreachable."""


def _client() -> docker.DockerClient:
    """Return a fresh DockerClient. Lets DOCKER_HOST override the default
    unix socket. Each call is cheap (it's just a thin wrapper)."""
    try:
        return docker.from_env()
    except docker.errors.DockerException as e:  # pragma: no cover - depends on host
        raise DockerMonError(f"docker daemon unavailable: {e}") from e


def _validate_id_or_name(container_id: str) -> str:
    if not isinstance(container_id, str) or not _ID_OR_NAME_RE.match(container_id):
        raise ValueError(f"invalid container id/name: {container_id!r}")
    return container_id


def _strip_name(name: str | None) -> str:
    if not name:
        return ""
    return name.lstrip("/")


def _ports_summary(ports: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Compact representation of a container's port mapping.

    Docker returns ``{"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}``.
    Flatten it into one row per binding so the UI can render a table.
    """
    out: list[dict[str, Any]] = []
    for spec, bindings in (ports or {}).items():
        proto = "tcp"
        cport: str = spec
        if "/" in spec:
            cport, proto = spec.split("/", 1)
        if not bindings:
            out.append({
                "container_port": cport,
                "proto": proto,
                "host_ip": None,
                "host_port": None,
            })
            continue
        for b in bindings:
            out.append({
                "container_port": cport,
                "proto": proto,
                "host_ip": b.get("HostIp") or None,
                "host_port": b.get("HostPort") or None,
            })
    return out


def _filter_env(env_list: Iterable[str] | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for raw in env_list or []:
        if not isinstance(raw, str) or "=" not in raw:
            continue
        key, val = raw.split("=", 1)
        if key.startswith(_SAFE_ENV_PREFIXES):
            out.append({"key": key, "value": val})
        else:
            out.append({"key": key, "value": "***"})
    return out


def _health_state(attrs: dict[str, Any]) -> str | None:
    state = (attrs.get("State") or {})
    health = state.get("Health") or {}
    status = health.get("Status")
    return status if isinstance(status, str) else None


def _container_summary(c: Any) -> dict[str, Any]:
    """Compact dict suitable for the list view."""
    attrs: dict[str, Any] = c.attrs or {}
    state = attrs.get("State") or {}
    return {
        "id": c.id,
        "short_id": c.short_id,
        "name": _strip_name(c.name),
        "image": (c.image.tags[0] if c.image and c.image.tags else (attrs.get("Config") or {}).get("Image", "")),
        "status": c.status,
        "state": state.get("Status") or c.status,
        "created": attrs.get("Created"),
        "ports": _ports_summary(attrs.get("NetworkSettings", {}).get("Ports") or {}),
        "labels": (attrs.get("Config") or {}).get("Labels") or {},
        "health": _health_state(attrs),
    }


def list_containers(all: bool = False) -> list[dict[str, Any]]:
    """List containers. ``all=True`` includes stopped containers."""
    try:
        cl = _client()
        containers = cl.containers.list(all=bool(all))
    except APIError as e:
        raise DockerMonError(f"docker API error: {e}") from e
    return [_container_summary(c) for c in containers]


def get_container(container_id: str) -> dict[str, Any]:
    """Full detail for a single container — surfaces config, mounts, networks,
    filtered env, command, restart policy, and current state."""
    cid = _validate_id_or_name(container_id)
    try:
        cl = _client()
        c = cl.containers.get(cid)
    except NotFound as e:
        raise DockerMonError(f"container not found: {cid}") from e
    except APIError as e:
        raise DockerMonError(f"docker API error: {e}") from e

    attrs: dict[str, Any] = c.attrs or {}
    config: dict[str, Any] = attrs.get("Config") or {}
    host_config: dict[str, Any] = attrs.get("HostConfig") or {}
    network_settings: dict[str, Any] = attrs.get("NetworkSettings") or {}
    networks_raw: dict[str, Any] = network_settings.get("Networks") or {}
    networks: dict[str, dict[str, Any]] = {}
    for nname, ndata in networks_raw.items():
        if not isinstance(ndata, dict):
            continue
        networks[nname] = {
            "ip_address": ndata.get("IPAddress") or None,
            "gateway": ndata.get("Gateway") or None,
            "mac_address": ndata.get("MacAddress") or None,
            "network_id": ndata.get("NetworkID") or None,
        }

    mounts: list[dict[str, Any]] = []
    for m in attrs.get("Mounts") or []:
        if not isinstance(m, dict):
            continue
        mounts.append({
            "type": m.get("Type"),
            "source": m.get("Source"),
            "destination": m.get("Destination"),
            "mode": m.get("Mode"),
            "rw": m.get("RW"),
        })

    cmd = config.get("Cmd")
    entrypoint = config.get("Entrypoint")
    return {
        "id": c.id,
        "short_id": c.short_id,
        "name": _strip_name(c.name),
        "image": (c.image.tags[0] if c.image and c.image.tags else config.get("Image", "")),
        "image_id": (c.image.id if c.image else None),
        "status": c.status,
        "state": (attrs.get("State") or {}).get("Status") or c.status,
        "created": attrs.get("Created"),
        "started_at": (attrs.get("State") or {}).get("StartedAt"),
        "finished_at": (attrs.get("State") or {}).get("FinishedAt"),
        "exit_code": (attrs.get("State") or {}).get("ExitCode"),
        "command": cmd if isinstance(cmd, list) else ([cmd] if cmd else []),
        "entrypoint": entrypoint if isinstance(entrypoint, list) else ([entrypoint] if entrypoint else []),
        "working_dir": config.get("WorkingDir") or None,
        "user": config.get("User") or None,
        "labels": config.get("Labels") or {},
        "env": _filter_env(config.get("Env") or []),
        "ports": _ports_summary(network_settings.get("Ports") or {}),
        "mounts": mounts,
        "network_mode": host_config.get("NetworkMode"),
        "networks": networks,
        "restart_policy": host_config.get("RestartPolicy") or {},
        "health": _health_state(attrs),
    }


def get_container_stats(container_id: str) -> dict[str, Any]:
    """One-shot stats sample. Returns a compact dict the UI/agent can render
    directly. Computation matches ``docker stats`` semantics."""
    cid = _validate_id_or_name(container_id)
    try:
        cl = _client()
        c = cl.containers.get(cid)
        s = c.stats(stream=False, decode=False)
    except NotFound as e:
        raise DockerMonError(f"container not found: {cid}") from e
    except APIError as e:
        raise DockerMonError(f"docker API error: {e}") from e

    cpu = s.get("cpu_stats") or {}
    pre_cpu = s.get("precpu_stats") or {}
    cpu_total = (cpu.get("cpu_usage") or {}).get("total_usage") or 0
    pre_total = (pre_cpu.get("cpu_usage") or {}).get("total_usage") or 0
    sys_total = cpu.get("system_cpu_usage") or 0
    pre_sys_total = pre_cpu.get("system_cpu_usage") or 0
    online_cpus = cpu.get("online_cpus") or len((cpu.get("cpu_usage") or {}).get("percpu_usage") or []) or 1

    cpu_delta = max(0, cpu_total - pre_total)
    sys_delta = max(0, sys_total - pre_sys_total)
    cpu_percent = 0.0
    if sys_delta > 0 and cpu_delta > 0:
        cpu_percent = (cpu_delta / sys_delta) * float(online_cpus) * 100.0

    mem = s.get("memory_stats") or {}
    mem_used = int(mem.get("usage") or 0)
    # Docker counts cache; the popular ``docker stats`` formula subtracts it.
    cache = ((mem.get("stats") or {}).get("cache")
             or (mem.get("stats") or {}).get("inactive_file") or 0)
    mem_used_no_cache = max(0, mem_used - int(cache))
    mem_limit = int(mem.get("limit") or 0)
    mem_percent = (mem_used_no_cache / mem_limit) * 100.0 if mem_limit else 0.0

    rx = 0
    tx = 0
    for _iface, data in (s.get("networks") or {}).items():
        if isinstance(data, dict):
            rx += int(data.get("rx_bytes") or 0)
            tx += int(data.get("tx_bytes") or 0)

    blk_read = 0
    blk_write = 0
    for entry in ((s.get("blkio_stats") or {}).get("io_service_bytes_recursive") or []):
        op = (entry.get("op") or "").lower()
        if op in ("read",):
            blk_read += int(entry.get("value") or 0)
        elif op in ("write",):
            blk_write += int(entry.get("value") or 0)

    return {
        "id": c.id,
        "short_id": c.short_id,
        "name": _strip_name(c.name),
        "ts": time.time(),
        "cpu_percent": round(float(cpu_percent), 2),
        "online_cpus": int(online_cpus),
        "memory_usage": int(mem_used_no_cache),
        "memory_limit": int(mem_limit),
        "memory_percent": round(float(mem_percent), 2),
        "net_rx": int(rx),
        "net_tx": int(tx),
        "block_read": int(blk_read),
        "block_write": int(blk_write),
    }


# ---- Log streaming -------------------------------------------------------

def _strip_log_frame(chunk: bytes) -> bytes:
    """Strip Docker's 8-byte multiplex header.

    When TTY is disabled, Docker prefixes each frame with:
      [stream:1][pad:3][size:4][payload...]
    where stream is 0x01 (stdout) / 0x02 (stderr) / 0x00 (stdin).
    We accept any frame whose first byte is in {0x00, 0x01, 0x02} AND whose
    size header matches the remaining payload length; otherwise return the
    chunk untouched (TTY-mode containers stream raw text).
    """
    if not chunk or len(chunk) < 8:
        return chunk
    if chunk[0] not in (0x00, 0x01, 0x02):
        return chunk
    try:
        size = struct.unpack(">I", chunk[4:8])[0]
    except struct.error:
        return chunk
    body = chunk[8:]
    if size == len(body):
        return body
    # Multi-frame buffer: walk and concatenate stripped payloads.
    out = bytearray()
    i = 0
    while i + 8 <= len(chunk):
        if chunk[i] not in (0x00, 0x01, 0x02):
            return chunk
        try:
            sz = struct.unpack(">I", chunk[i + 4:i + 8])[0]
        except struct.error:
            return chunk
        start = i + 8
        end = start + sz
        if end > len(chunk):
            return chunk
        out.extend(chunk[start:end])
        i = end
    return bytes(out)


async def stream_logs(
    container_id: str,
    tail: int = 200,
    follow: bool = True,
) -> AsyncIterator[str]:
    """Async generator yielding decoded log lines.

    Reads the (blocking) docker SDK iterator on a worker thread and pumps
    bytes through an asyncio.Queue so the event loop never stalls. Strips the
    8-byte multiplex header when present and decodes with errors=replace.
    """
    cid = _validate_id_or_name(container_id)
    tail_n = max(1, min(int(tail or 200), 5000))
    try:
        cl = _client()
        c = cl.containers.get(cid)
    except NotFound as e:
        raise DockerMonError(f"container not found: {cid}") from e
    except APIError as e:
        raise DockerMonError(f"docker API error: {e}") from e

    queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=1024)
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _producer() -> None:
        try:
            it = c.logs(
                stream=True,
                follow=bool(follow),
                tail=tail_n,
                stdout=True,
                stderr=True,
                timestamps=False,
            )
            for raw in it:
                if stop.is_set():
                    break
                if not raw:
                    continue
                if isinstance(raw, str):
                    raw = raw.encode("utf-8", errors="replace")
                payload = _strip_log_frame(raw)
                fut = asyncio.run_coroutine_threadsafe(queue.put(payload), loop)
                try:
                    fut.result(timeout=10)
                except Exception:
                    break
        except Exception as e:  # pragma: no cover - daemon may go away
            logger.debug("docker log producer ended: %r", e)
        finally:
            try:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result(timeout=2)
            except Exception:
                pass

    worker = asyncio.create_task(asyncio.to_thread(_producer))

    pending = bytearray()
    try:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            pending.extend(chunk)
            while True:
                idx = pending.find(b"\n")
                if idx < 0:
                    break
                line_bytes = bytes(pending[:idx])
                del pending[: idx + 1]
                yield line_bytes.decode("utf-8", errors="replace").rstrip("\r")
        # Flush trailing partial line.
        if pending:
            yield bytes(pending).decode("utf-8", errors="replace").rstrip("\r")
    finally:
        stop.set()
        if not worker.done():
            worker.cancel()
        # Drain quietly.
        try:
            await asyncio.wait_for(asyncio.shield(worker), timeout=2)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            pass


# ---- Lifecycle actions ---------------------------------------------------

_VALID_ACTIONS: frozenset[str] = frozenset(
    {"start", "stop", "restart", "pause", "unpause", "kill"}
)


def container_action(container_id: str, action: str) -> dict[str, Any]:
    """Execute a lifecycle action on the named container."""
    cid = _validate_id_or_name(container_id)
    a = (action or "").strip().lower()
    if a not in _VALID_ACTIONS:
        raise ValueError(f"invalid action: {action!r}")
    try:
        cl = _client()
        c = cl.containers.get(cid)
        method = getattr(c, a)
        method()
        c.reload()
    except NotFound as e:
        raise DockerMonError(f"container not found: {cid}") from e
    except APIError as e:
        raise DockerMonError(f"docker API error: {e}") from e
    state = (c.attrs.get("State") or {}).get("Status") or c.status
    return {"ok": True, "state": state, "id": c.id, "name": _strip_name(c.name)}
