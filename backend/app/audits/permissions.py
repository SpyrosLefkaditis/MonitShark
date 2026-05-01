"""Audit filesystem permissions under /host/etc and SUID-root bins under /host/usr."""
from __future__ import annotations

import grp
import hashlib
import os
import stat
import time
from pathlib import Path

from app.audits import register
from app.schemas import AuditReport, Finding
from app.util.paths import HOST_ROOT

_ETC = HOST_ROOT / "etc"
_BIN_DIRS: tuple[Path, ...] = (HOST_ROOT / "usr" / "bin", HOST_ROOT / "usr" / "sbin")
_SHADOW = _ETC / "shadow"

# Hard caps to keep the audit fast on large hosts.
_ETC_SCAN_LIMIT = 5000
_WORLD_WRITABLE_MAX = 50
_SUID_MAX = 50

# Standard SUID-root binaries on Debian/Ubuntu/Fedora/RHEL — anything else is
# worth flagging for review, even if benign.
_SUID_ALLOWLIST: frozenset[str] = frozenset({
    "sudo", "mount", "umount", "passwd", "chsh", "chfn", "gpasswd", "newgrp",
    "su", "pkexec", "chage", "expiry", "crontab", "at", "ping", "ping6",
    "fusermount", "fusermount3", "dotlockfile", "ssh-agent", "Xorg",
    "polkit-agent-helper-1", "unix_chkpwd", "pam_timestamp_check",
})

# Substring patterns we treat as "sensitive content directories or files" when
# evaluating world-readable bits under /host/etc.
_SENSITIVE_PATTERNS: tuple[str, ...] = (
    "/secrets/", "/private/",
)
_SENSITIVE_BASENAMES: frozenset[str] = frozenset({".env"})


def _fid(check: str, evidence: str) -> str:
    """Deterministic Finding.id keyed on check + evidence string."""
    return f"permissions.{check}.{hashlib.sha1(evidence.encode()).hexdigest()[:10]}"


def _now() -> float:
    return time.time()


def _is_world_writable(mode: int) -> bool:
    return bool(mode & stat.S_IWOTH)


def _is_world_readable(mode: int) -> bool:
    return bool(mode & stat.S_IROTH)


def _is_suid_root(st: os.stat_result) -> bool:
    return bool(st.st_mode & stat.S_ISUID) and st.st_uid == 0


def _looks_sensitive(path: str) -> bool:
    p = path.lower()
    if any(pat in p for pat in _SENSITIVE_PATTERNS):
        return True
    base = os.path.basename(p)
    return base in _SENSITIVE_BASENAMES


def _gid_name(gid: int) -> str:
    try:
        return grp.getgrgid(gid).gr_name
    except (KeyError, OSError):
        return ""


def _scan_etc(now: float) -> list[Finding]:
    """Walk /host/etc bounded by _ETC_SCAN_LIMIT; emit findings for world-writable
    files and world-readable secret-style files."""
    findings: list[Finding] = []
    seen: set[str] = set()
    ww_count = 0
    scanned = 0

    if not _ETC.exists():
        return findings

    for dirpath, dirnames, filenames in os.walk(_ETC, followlinks=False):
        # Skip noisy/never-relevant subtrees.
        dirnames[:] = [d for d in dirnames if d not in (".git",)]
        for name in filenames:
            if scanned >= _ETC_SCAN_LIMIT:
                return findings
            scanned += 1
            full = os.path.join(dirpath, name)
            try:
                st = os.lstat(full)
            except OSError:
                continue
            if stat.S_ISLNK(st.st_mode):
                continue
            mode = st.st_mode

            if _is_world_writable(mode) and not stat.S_ISDIR(mode):
                if full in seen or ww_count >= _WORLD_WRITABLE_MAX:
                    continue
                seen.add(full)
                ww_count += 1
                findings.append(Finding(
                    id=_fid("world_writable_etc", full),
                    category="permissions",
                    severity="medium",
                    title=f"World-writable file under /etc: {full[len(str(HOST_ROOT)):]}",
                    description=(
                        "Any local user can modify this file. Files in /etc "
                        "drive system behavior, so a world-writable entry is a "
                        "common privilege-escalation foothold. The fix removes "
                        "the world-write bit (`chmod o-w`)."
                    ),
                    evidence={"path": full, "mode": oct(mode & 0o7777)},
                    fix_id="permissions.world_writable_in_etc",
                    status="open",
                    created_at=now,
                ))

            if _is_world_readable(mode) and _looks_sensitive(full):
                if full in seen:
                    continue
                seen.add(full)
                findings.append(Finding(
                    id=_fid("world_readable_secret", full),
                    category="permissions",
                    severity="high",
                    title=f"World-readable secret file: {full[len(str(HOST_ROOT)):]}",
                    description=(
                        "This file matches a secrets-style path or name "
                        "(.env / secrets / private) yet is readable by every "
                        "local user. Tighten the mode (`chmod o-rwx`) and "
                        "review what credentials it exposes."
                    ),
                    evidence={"path": full, "mode": oct(mode & 0o7777)},
                    fix_id=None,
                    status="open",
                    created_at=now,
                ))
    return findings


def _shadow_finding(now: float) -> Finding | None:
    """Check that /etc/shadow has tight ownership + mode."""
    try:
        st = os.lstat(_SHADOW)
    except OSError:
        return None
    mode = st.st_mode & 0o7777
    gname = _gid_name(st.st_gid)
    mode_ok = mode in (0o640, 0o600, 0o000)  # 0000 on some hardened distros (root reads via root)
    group_ok = gname in ("shadow", "root", "")
    if mode_ok and group_ok:
        return None
    return Finding(
        id=_fid("shadow_perms", f"{_SHADOW}:{oct(mode)}:{gname}"),
        category="permissions",
        severity="high",
        title="/etc/shadow has unexpected permissions or group",
        description=(
            "/etc/shadow stores hashed passwords and should be owned root:root "
            "or root:shadow with mode 0640 (or stricter). Anything else risks "
            "leaking hashes to non-privileged users. Restore the expected "
            "owner/mode (`chown root:shadow /etc/shadow && chmod 0640 /etc/shadow`)."
        ),
        evidence={
            "path": str(_SHADOW),
            "mode": oct(mode),
            "group": gname,
            "uid": st.st_uid,
            "gid": st.st_gid,
        },
        fix_id=None,
        status="open",
        created_at=now,
    )


def _scan_suid(now: float) -> list[Finding]:
    """Find SUID-root bins that aren't on the standard allowlist."""
    findings: list[Finding] = []
    count = 0
    for d in _BIN_DIRS:
        if not d.exists():
            continue
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for entry in entries:
            if count >= _SUID_MAX:
                return findings
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            if not _is_suid_root(st):
                continue
            base = entry.name
            if base in _SUID_ALLOWLIST:
                continue
            count += 1
            full = entry.path
            findings.append(Finding(
                id=_fid("suid_unexpected", full),
                category="permissions",
                severity="medium",
                title=f"Unexpected SUID-root binary: {base}",
                description=(
                    f"{full} runs with root privileges via the SUID bit and "
                    "is not on MonitShark's standard allowlist. Verify the package "
                    "that provides it, and consider removing the SUID bit "
                    "(`chmod u-s`) if the binary does not need it."
                ),
                evidence={
                    "path": full,
                    "mode": oct(st.st_mode & 0o7777),
                    "uid": st.st_uid,
                },
                fix_id=None,
                status="open",
                created_at=now,
            ))
    return findings


@register("permissions")
async def audit_permissions() -> AuditReport:
    """Bounded scan of /host/etc + SUID checks on /host/usr/{bin,sbin}."""
    now = _now()
    findings: list[Finding] = []
    findings.extend(_scan_etc(now))
    sf = _shadow_finding(now)
    if sf is not None:
        findings.append(sf)
    findings.extend(_scan_suid(now))
    return AuditReport(name="permissions", findings=findings)
