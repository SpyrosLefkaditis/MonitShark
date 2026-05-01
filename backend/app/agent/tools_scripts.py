"""@tool wrappers for the user-script subsystem.

Read-only: list_scripts, get_script.
Destructive (require confirmation gate): save_script, delete_script,
run_script, install_script_as_service, schedule_script_via_cron.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app import scripts as scripts_mod


@tool
def list_scripts() -> list[dict]:
    """List bash scripts saved under /opt/cockpit/scripts. Each entry has the
    script name, size in bytes, modified timestamp, and whether it is executable.
    These scripts can be run, scheduled via cron, or installed as systemd units."""
    return scripts_mod.list_scripts()


@tool
def get_script(name: str) -> dict:
    """Return the full content of a saved script by name (without the .sh suffix).
    Use this to read what a script does before running or modifying it."""
    return scripts_mod.get_script(name)


@tool
def save_script(name: str, content: str, make_executable: bool = True) -> dict:
    """Create or overwrite a bash script under /opt/cockpit/scripts.
    `name` must match ^[a-zA-Z0-9_-]{1,64}$ (no .sh suffix). Content is written
    as-is (cap 1 MiB). When make_executable is True the file is chmod 755."""
    return scripts_mod.save_script(name=name, content=content, make_executable=make_executable)


@tool
def delete_script(name: str) -> dict:
    """Remove a saved script from /opt/cockpit/scripts."""
    return scripts_mod.delete_script(name)


@tool
def run_script(name: str, args: list[str] | None = None, timeout_s: int = 60) -> dict:
    """Run a saved script ad hoc. Args must be plain identifier-like strings
    (no shell metachars). Timeout capped at 300 seconds. Returns rc/stdout/stderr."""
    return scripts_mod.run_script(name=name, args=list(args or []), timeout_s=timeout_s)


@tool
def install_script_as_service(
    script_name: str,
    service_name: str,
    description: str = "",
    restart: str = "no",
) -> dict:
    """Install a saved script as a oneshot systemd unit at
    /etc/systemd/system/<service_name>.service and run `systemctl daemon-reload`.
    Does NOT enable or start the unit — the caller can do that from the Services
    page. `restart` is one of: no, always, on-failure, on-abnormal."""
    return scripts_mod.install_as_service(
        script_name=script_name,
        service_name=service_name,
        description=description,
        restart=restart,
    )


@tool
def schedule_script_via_cron(
    script_name: str,
    schedule: str,
    user: str = "root",
) -> dict:
    """Schedule a saved script via cron. `schedule` is a 5-field cron expression
    or @-alias (@daily/@hourly/etc). `user` defaults to root."""
    return scripts_mod.schedule_via_cron(
        script_name=script_name,
        schedule=schedule,
        user=user,
    )


TOOLS: list[Any] = [
    list_scripts,
    get_script,
    save_script,
    delete_script,
    run_script,
    install_script_as_service,
    schedule_script_via_cron,
]

DESTRUCTIVE_NAMES: set[str] = {
    "save_script",
    "delete_script",
    "run_script",
    "install_script_as_service",
    "schedule_script_via_cron",
}
