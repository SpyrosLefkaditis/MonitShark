"""Audit /host/etc/passwd, /etc/sudoers, and /etc/sudoers.d/* for risky entries."""
from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

from app.audits import register
from app.schemas import AuditReport, Finding
from app.util.paths import HOST_ROOT, PASSWD_FILE, SUDOERS_D, SUDOERS_FILE

_LOGIN_SHELLS: frozenset[str] = frozenset({
    "/bin/bash", "/bin/sh", "/bin/zsh", "/bin/dash", "/bin/ksh", "/bin/tcsh",
    "/bin/fish", "/usr/bin/bash", "/usr/bin/sh", "/usr/bin/zsh",
    "/usr/bin/dash", "/usr/bin/ksh", "/usr/bin/tcsh", "/usr/bin/fish",
})

# Matches lines like:
#   alice ALL=(ALL) NOPASSWD: ALL
#   alice ALL=(ALL:ALL) NOPASSWD:ALL
#   %wheel ALL=(ALL) NOPASSWD: ALL
# We tolerate extra whitespace, mixed case, optional second runas group.
_SUDO_RE = re.compile(
    r"^\s*(?P<who>[%@]?[A-Za-z0-9_.\-]+)\s+"
    r"(?P<host>\S+)\s*=\s*"
    r"\((?P<runas>[^)]+)\)\s*"
    r"(?P<tags>(?:[A-Z_]+\s*:\s*)*)"
    r"(?P<cmds>.+?)\s*$"
)


def _fid(check: str, evidence: str) -> str:
    """Deterministic Finding.id keyed on check + evidence string."""
    return f"users.{check}.{hashlib.sha1(evidence.encode()).hexdigest()[:10]}"


def _now() -> float:
    return time.time()


def _host_path(p: Path) -> Path:
    """Map a logical /etc path under PASSWD_FILE.parent to its /host counterpart."""
    return p


def _read_or_empty(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return ""


def _parse_passwd(text: str) -> list[tuple[str, str, int, int, str, str, str]]:
    """Parse /etc/passwd into structured tuples; skip malformed lines."""
    out: list[tuple[str, str, int, int, str, str, str]] = []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) < 7:
            continue
        name, passwd, uid_s, gid_s, gecos, home, shell = parts[:7]
        try:
            uid = int(uid_s)
            gid = int(gid_s)
        except ValueError:
            continue
        out.append((name, passwd, uid, gid, gecos, home, shell))
    return out


def _strip_sudoers_comments(text: str) -> list[tuple[int, str]]:
    """Yield (1-based line number, content) tuples with comments + blanks dropped."""
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append((i, line))
    return out


def _check_sudo_rule(line: str) -> tuple[bool, dict] | None:
    """Inspect a sudoers line. Returns (is_unrestricted_nopasswd, details) or None."""
    m = _SUDO_RE.match(line)
    if not m:
        return None
    who = m.group("who")
    runas = m.group("runas").strip()
    tags = m.group("tags") or ""
    cmds = m.group("cmds").strip()
    nopasswd = "NOPASSWD" in tags.upper()
    # "Full unrestricted access" is the canonical pattern: runas includes ALL
    # and the command list is exactly ALL (or ALL,!something — ignore exclusions).
    runas_all = "ALL" in {t.strip().upper() for t in runas.replace(":", ",").split(",")}
    cmds_all = cmds.upper() == "ALL"
    return (nopasswd and runas_all and cmds_all), {
        "who": who,
        "runas": runas,
        "tags": tags.strip(),
        "cmds": cmds,
    }


def _iter_sudoers_files() -> list[Path]:
    """Return every readable sudoers file (main + sudoers.d/*)."""
    files: list[Path] = []
    if SUDOERS_FILE.exists():
        files.append(SUDOERS_FILE)
    if SUDOERS_D.exists() and SUDOERS_D.is_dir():
        try:
            for entry in sorted(SUDOERS_D.iterdir()):
                # sudo skips files with `.` or `~`; mirror that to reduce noise.
                if entry.name.startswith(".") or entry.name.endswith("~"):
                    continue
                if entry.is_file():
                    files.append(entry)
        except OSError:
            pass
    return files


@register("users")
async def audit_users() -> AuditReport:
    """Inspect users + sudoers for duplicate UID 0, blank passwords, missing
    home dirs on login accounts, and unrestricted NOPASSWD sudo grants."""
    findings: list[Finding] = []
    now = _now()

    if not PASSWD_FILE.exists():
        findings.append(Finding(
            id=_fid("passwd_missing", str(PASSWD_FILE)),
            category="users",
            severity="info",
            title="/etc/passwd not found",
            description=(
                "Could not find /etc/passwd on the host. The user audit cannot "
                "run without it."
            ),
            evidence={"path": str(PASSWD_FILE)},
            fix_id=None,
            status="open",
            created_at=now,
        ))
        return AuditReport(name="users", findings=findings)

    passwd_text = _read_or_empty(PASSWD_FILE)
    rows = _parse_passwd(passwd_text)

    # Duplicate UID 0 (one finding per non-root entry).
    uid0 = [r for r in rows if r[2] == 0]
    if len(uid0) > 1:
        for name, _pw, _uid, _gid, _gecos, _home, _shell in uid0:
            if name == "root":
                continue
            ev = f"uid0:{name}"
            findings.append(Finding(
                id=_fid("uid0_duplicate", ev),
                category="users",
                severity="critical",
                title=f"Account '{name}' shares UID 0 with root",
                description=(
                    f"User '{name}' is configured with UID 0, the same as "
                    "root. UID, not the username, is what the kernel checks "
                    "for root privileges, so this account has unrestricted "
                    "system access. Investigate and remove or change its UID."
                ),
                evidence={"username": name, "uid": 0},
                fix_id=None,
                status="open",
                created_at=now,
            ))

    # Genuinely passwordless accounts (passwd field is empty, not '!' / '*').
    for name, pw, _uid, _gid, _gecos, _home, _shell in rows:
        if pw == "":
            ev = f"empty_passwd:{name}"
            findings.append(Finding(
                id=_fid("passwordless", ev),
                category="users",
                severity="high",
                title=f"Account '{name}' has no password",
                description=(
                    f"The /etc/passwd entry for '{name}' has an empty password "
                    "field. On many distros that means the account can log in "
                    "with no credentials. Lock it (`passwd -l`) or set a "
                    "password / disable the shell."
                ),
                evidence={"username": name},
                fix_id=None,
                status="open",
                created_at=now,
            ))

    # Login shells with a missing home directory.
    for name, _pw, _uid, _gid, _gecos, home, shell in rows:
        if shell not in _LOGIN_SHELLS:
            continue
        if not home:
            continue
        # Translate /home/foo to /host/home/foo so we can stat from inside the container.
        host_home = HOST_ROOT / home.lstrip("/")
        if not host_home.exists():
            ev = f"missing_home:{name}:{home}"
            findings.append(Finding(
                id=_fid("missing_home", ev),
                category="users",
                severity="low",
                title=f"User '{name}' has a login shell but no home directory",
                description=(
                    f"User '{name}' is configured with login shell '{shell}' "
                    f"but their home directory '{home}' does not exist. "
                    "Either create the directory with the right ownership or "
                    "change the user's shell to /usr/sbin/nologin."
                ),
                evidence={"username": name, "home": home, "shell": shell},
                fix_id=None,
                status="open",
                created_at=now,
            ))

    # Sudoers parsing.
    for spath in _iter_sudoers_files():
        text = _read_or_empty(spath)
        if not text:
            continue
        for lineno, content in _strip_sudoers_comments(text):
            checked = _check_sudo_rule(content)
            if checked is None:
                continue
            unrestricted, info = checked
            who: str = info["who"]
            ev_base = f"{spath.name}:{lineno}:{who}:{info['cmds']}"
            if unrestricted and "NOPASSWD" in (info["tags"] or "").upper():
                if who.startswith("%") or who.startswith("@"):
                    # Group/netgroup-based grants are noted as info only.
                    findings.append(Finding(
                        id=_fid("sudo_group_nopasswd", ev_base),
                        category="users",
                        severity="info",
                        title=f"Group sudo grant: {who} ALL=(ALL) NOPASSWD: ALL",
                        description=(
                            f"In {spath} at line {lineno}, group '{who}' has "
                            "passwordless sudo to run any command. Group-based "
                            "grants are common (e.g. %wheel) — verify the "
                            "membership of the group is intentional and small."
                        ),
                        evidence={
                            "file": str(spath),
                            "line_number": lineno,
                            **info,
                        },
                        fix_id=None,
                        status="open",
                        created_at=now,
                    ))
                else:
                    findings.append(Finding(
                        id=_fid("sudo_user_nopasswd", ev_base),
                        category="users",
                        severity="high",
                        title=f"User '{who}' has unrestricted passwordless sudo",
                        description=(
                            f"In {spath} at line {lineno}, user '{who}' is "
                            "granted (ALL) NOPASSWD: ALL — they can run any "
                            "command as any user without re-typing their "
                            "password. Remove the NOPASSWD tag or restrict the "
                            "command list."
                        ),
                        evidence={
                            "file": str(spath),
                            "line_number": lineno,
                            **info,
                        },
                        fix_id=None,
                        status="open",
                        created_at=now,
                    ))

    return AuditReport(name="users", findings=findings)
