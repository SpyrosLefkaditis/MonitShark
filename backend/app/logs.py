"""Log tail + grep over /host/var/log with path allowlist.

The UI talks in display paths (no /host prefix). Internally we always resolve
under HOST_ROOT and verify against LOG_ROOTS.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.schemas import LogSearchIn, LogSearchOut, LogTailOut
from app.util.paths import HOST_ROOT, LOG_ROOTS, resolve_safe

_HOST_PREFIX = str(HOST_ROOT)
_DEFAULT_SOURCES = (
    "auth.log",
    "syslog",
    "dpkg.log",
    "messages",
    "secure",
    "dnf.log",
)
_TAIL_LINES_CAP = 2000
_TAIL_BYTES_PER_LINE = 200
_TAIL_MAX_READ = 4 * 1024 * 1024  # 4 MiB
_SEARCH_MATCHES_CAP = 1000
_SEARCH_SCAN_LINES = 50_000


def _to_internal(path: str) -> Path:
    """Map a display path (e.g. /var/log/auth.log) to /host/var/log/auth.log."""
    raw = path.strip()
    if not raw:
        raise ValueError("empty path")
    if raw.startswith(_HOST_PREFIX):
        return Path(raw)
    if not raw.startswith("/"):
        raw = "/" + raw
    return Path(_HOST_PREFIX + raw)


def _to_display(p: Path) -> str:
    s = str(p)
    if s.startswith(_HOST_PREFIX):
        return s[len(_HOST_PREFIX):]
    return s


def list_sources() -> list[str]:
    """Return curated, existing log paths under /host/var/log/ (display form)."""
    base = HOST_ROOT / "var" / "log"
    out: list[str] = []
    for name in _DEFAULT_SOURCES:
        p = base / name
        if p.exists() and p.is_file():
            out.append(_to_display(p))
    return out


def _read_tail(path: Path, n: int) -> list[str]:
    """Read approximately the last n lines of a (possibly large) file."""
    n = max(1, min(int(n), _TAIL_LINES_CAP))
    want = min(n * _TAIL_BYTES_PER_LINE, _TAIL_MAX_READ)
    try:
        size = path.stat().st_size
    except OSError:
        return []
    read_from = max(0, size - want)
    with path.open("rb") as fh:
        fh.seek(read_from)
        chunk = fh.read(size - read_from)
    text = chunk.decode("utf-8", errors="replace")
    lines = text.splitlines()
    # If we didn't start at offset 0, the first line may be partial — drop it.
    if read_from > 0 and lines:
        lines = lines[1:]
    return lines[-n:]


def tail(path: str, lines: int = 200) -> LogTailOut:
    """Return the last N lines of an allowlisted log file."""
    internal = _to_internal(path)
    resolved = resolve_safe(internal, LOG_ROOTS)
    n = max(1, min(int(lines), _TAIL_LINES_CAP))
    out_lines = _read_tail(resolved, n)
    return LogTailOut(path=_to_display(resolved), lines=out_lines)


def search(payload: LogSearchIn) -> LogSearchOut:
    """Tail-first regex/substring search over an allowlisted log file."""
    internal = _to_internal(payload.path)
    resolved = resolve_safe(internal, LOG_ROOTS)
    cap = max(1, min(int(payload.max_matches), _SEARCH_MATCHES_CAP))

    if payload.regex:
        try:
            pattern = re.compile(payload.query)
        except re.error as e:
            raise ValueError(f"invalid regex: {e}") from e
        predicate = lambda line: bool(pattern.search(line))  # noqa: E731
    else:
        needle = payload.query
        predicate = lambda line: needle in line  # noqa: E731

    matches: list[str] = []
    # Read all (bounded) lines, scan tail-first so we return the most recent.
    with resolved.open("r", encoding="utf-8", errors="replace") as fh:
        all_lines = fh.readlines()
    if len(all_lines) > _SEARCH_SCAN_LINES:
        all_lines = all_lines[-_SEARCH_SCAN_LINES:]
    for line in reversed(all_lines):
        stripped = line.rstrip("\n")
        if predicate(stripped):
            matches.append(stripped)
            if len(matches) >= cap:
                break
    return LogSearchOut(path=_to_display(resolved), matches=matches)
