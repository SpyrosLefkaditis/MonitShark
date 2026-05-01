"""Path allowlist resolution. Every path entering the backend from a tool or
HTTP param goes through `resolve_safe` against an allowed root."""
from __future__ import annotations

from pathlib import Path

HOST_ROOT = Path("/host")

LOG_ROOTS = [HOST_ROOT / "var" / "log"]
SCRIPT_ROOTS = [Path("/opt/cockpit/scripts")]
CRON_ROOTS = [
    HOST_ROOT / "var" / "spool" / "cron",
    HOST_ROOT / "etc" / "crontab",
    HOST_ROOT / "etc" / "cron.d",
]
SSHD_CONFIG = HOST_ROOT / "etc" / "ssh" / "sshd_config"
PASSWD_FILE = HOST_ROOT / "etc" / "passwd"
SUDOERS_FILE = HOST_ROOT / "etc" / "sudoers"
SUDOERS_D = HOST_ROOT / "etc" / "sudoers.d"
OS_RELEASE = HOST_ROOT / "etc" / "os-release"


class PathRejected(ValueError):
    """Path resolves outside any allowed root."""


def resolve_safe(path: str | Path, allowed_roots: list[Path]) -> Path:
    """Resolve symlinks/.. and verify the result lives under one of `allowed_roots`."""
    p = Path(path).expanduser()
    # Don't fail if the file doesn't exist yet — caller may be creating it.
    try:
        p = p.resolve(strict=False)
    except (OSError, RuntimeError) as e:
        raise PathRejected(f"cannot resolve {path}: {e}") from e
    for root in allowed_roots:
        try:
            r = root.resolve(strict=False)
            p.relative_to(r)
            return p
        except ValueError:
            continue
    raise PathRejected(f"{p} is not under any allowed root: {[str(r) for r in allowed_roots]}")
