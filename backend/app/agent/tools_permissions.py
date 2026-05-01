"""@tool wrappers for the host file-permission inspector/editor.

Read-only: list_dir, get_file_info.
Destructive (require confirmation gate): chmod_path, chown_path.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app import permissions as perms_mod


@tool
def list_dir(path: str) -> dict:
    """List the contents of a directory under one of the curated browseable roots
    (/etc, /opt/cockpit, /var/log, /home, /root). Returns name, mode, owner, group,
    size, and mtime per entry. Capped at 500 entries."""
    return perms_mod.list_dir(path)


@tool
def get_file_info(path: str) -> dict:
    """Return permission/owner/group/size/mtime for a single file or directory
    under the curated browseable roots."""
    return perms_mod.get_file_info(path)


@tool
def chmod_path(path: str, mode_octal: str) -> dict:
    """Change permissions on a file or directory. mode_octal is a 3- or 4-digit
    octal string like "0644", "755", "0700"."""
    return perms_mod.chmod_path(path=path, mode_octal=mode_octal)


@tool
def chown_path(path: str, owner: str | None = None, group: str | None = None) -> dict:
    """Change ownership of a file or directory. Either or both of owner / group may
    be supplied (validated against ^[a-z_][a-z0-9_-]*$). Uses the host's user database."""
    return perms_mod.chown_path(path=path, owner=owner, group=group)


TOOLS: list[Any] = [
    list_dir,
    get_file_info,
    chmod_path,
    chown_path,
]

DESTRUCTIVE_NAMES: set[str] = {
    "chmod_path",
    "chown_path",
}
