"""Prefix list for shelling out into the host's namespaces from a container.

Used because the backend container runs `pid: host` and bind-mounts `/` at
`/host`, but mutating commands need to execute IN the host's namespaces (so
`apt`, `dnf`, `useradd`, `systemctl`, etc. behave correctly).
"""
from __future__ import annotations


def nsenter(cmd: list[str]) -> list[str]:
    """Wrap a command to run it in host PID 1's namespaces."""
    return [
        "nsenter",
        "--target", "1",
        "--mount", "--uts", "--ipc", "--net", "--pid",
        "--",
        *cmd,
    ]
