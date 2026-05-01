"""System package update wrapper.

Detects the host package manager from /host/etc/os-release, then exposes
list / security-only-upgrade / full-upgrade primitives. All shell-out goes
through ``run()``; user input is not interpolated into commands here.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.util.nsenter import nsenter
from app.util.paths import OS_RELEASE
from app.util.sh import CommandRejected, run

_APT_DISTROS: frozenset[str] = frozenset({"debian", "ubuntu", "raspbian"})
_DNF_DISTROS: frozenset[str] = frozenset({"fedora", "rhel", "centos", "rocky", "almalinux"})


def _parse_os_release(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        out[k.strip().lower()] = v
    return out


def detect_pm() -> str:
    """Return ``"apt"``, ``"dnf"``, or ``"unknown"``."""
    p: Path = OS_RELEASE
    if not p.exists():
        return "unknown"
    try:
        text = p.read_text(errors="replace")
    except OSError:
        return "unknown"
    info = _parse_os_release(text)
    distro_id = info.get("id", "").lower()
    id_like = [t for t in info.get("id_like", "").lower().split() if t]
    candidates = {distro_id, *id_like}
    if candidates & _APT_DISTROS:
        return "apt"
    if candidates & _DNF_DISTROS:
        return "dnf"
    return "unknown"


# apt list --upgradable line shape:
#   name/dist[,otherdist] new-version arch [upgradable from: current-version]
_APT_LINE_RE = re.compile(
    r"^(?P<name>[^/\s]+)/(?P<dist>\S+)\s+(?P<new>\S+)\s+(?P<arch>\S+)\s+\[upgradable from:\s*(?P<cur>[^\]]+)\]\s*$",
)


def _apt_list_upgradable() -> list[dict]:
    cmd = nsenter(["apt", "list", "--upgradable"])
    try:
        cc = run(cmd, timeout=60, trust_args=True)
    except CommandRejected:
        return []
    out: list[dict] = []
    for raw in cc.stdout.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("listing"):
            continue
        m = _APT_LINE_RE.match(line)
        if not m:
            continue
        dist = m.group("dist")
        is_security = "security" in dist.lower()
        out.append({
            "package": m.group("name"),
            "current_version": m.group("cur").strip(),
            "new_version": m.group("new"),
            "arch": m.group("arch"),
            "source": "security" if is_security else dist,
            "is_security": is_security,
        })
    return out


def _dnf_security_packages() -> set[str]:
    cmd = nsenter(["dnf", "-q", "updateinfo", "list", "security"])
    try:
        cc = run(cmd, timeout=120, trust_args=True)
    except CommandRejected:
        return set()
    pkgs: set[str] = set()
    for raw in cc.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        # Format: "<advisory-id> <severity> <pkg-name-version-arch>"
        nvra = parts[-1]
        # Strip trailing arch and version segments to recover the bare name —
        # not exact, but good enough for joining against check-update rows.
        name = nvra
        for sep in (".x86_64", ".noarch", ".aarch64", ".i686", ".armv7hl", ".s390x", ".ppc64le"):
            if name.endswith(sep):
                name = name[: -len(sep)]
                break
        # Drop the trailing "-version-release" tail.
        head = name.rsplit("-", 2)
        if len(head) >= 2:
            name = head[0]
        pkgs.add(name)
    return pkgs


def _dnf_list_upgradable() -> list[dict]:
    cmd = nsenter(["dnf", "-q", "check-update", "--refresh"])
    try:
        cc = run(cmd, timeout=180, trust_args=True)
    except CommandRejected:
        return []
    # rc 100 = updates available; rc 0 = none; anything else = error.
    if cc.returncode not in (0, 100):
        return []
    security = _dnf_security_packages()
    out: list[dict] = []
    for raw in cc.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("Obsoleting") or line.startswith("Last metadata"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        head, new_version, repo = parts[0], parts[1], parts[2]
        # head is "<name>.<arch>".
        if "." in head:
            name, _, arch = head.rpartition(".")
        else:
            name, arch = head, ""
        is_security = name in security
        out.append({
            "package": name,
            "current_version": "",
            "new_version": new_version,
            "arch": arch,
            "source": "security" if is_security else repo,
            "is_security": is_security,
        })
    return out


def list_upgradable() -> list[dict]:
    """Return upgradable packages across the detected package manager."""
    pm = detect_pm()
    if pm == "apt":
        return _apt_list_upgradable()
    if pm == "dnf":
        return _dnf_list_upgradable()
    return []


def _wrap_result(cc) -> dict:
    return {
        "ok": cc.returncode == 0,
        "rc": cc.returncode,
        "stdout": cc.stdout,
        "stderr": cc.stderr,
    }


def upgrade_security_only() -> dict:
    """Apply only the security updates available on this host."""
    pm = detect_pm()
    if pm == "apt":
        # unattended-upgrade is the canonical "security only" path on apt.
        cmd = nsenter([
            "env", "DEBIAN_FRONTEND=noninteractive",
            "unattended-upgrade", "-v",
        ])
        try:
            cc = run(cmd, timeout=900, trust_args=True)
        except CommandRejected as e:
            return {"ok": False, "rc": -1, "stdout": "", "stderr": str(e)}
        return _wrap_result(cc)
    if pm == "dnf":
        cmd = nsenter(["dnf", "-y", "update", "--security"])
        try:
            cc = run(cmd, timeout=1800, trust_args=True)
        except CommandRejected as e:
            return {"ok": False, "rc": -1, "stdout": "", "stderr": str(e)}
        return _wrap_result(cc)
    return {
        "ok": False, "rc": -1, "stdout": "",
        "stderr": f"unsupported package manager: {pm}",
    }


def upgrade_all() -> dict:
    """Apply every pending update on this host."""
    pm = detect_pm()
    if pm == "apt":
        # Refresh the index first so the upgrade has a current view.
        cmd_update = nsenter([
            "env", "DEBIAN_FRONTEND=noninteractive",
            "apt-get", "update", "-qq",
        ])
        cmd_upgrade = nsenter([
            "env", "DEBIAN_FRONTEND=noninteractive",
            "apt-get", "-y", "-o", "Dpkg::Options::=--force-confold", "upgrade",
        ])
        try:
            up = run(cmd_update, timeout=180, trust_args=True)
            ug = run(cmd_upgrade, timeout=1800, trust_args=True)
        except CommandRejected as e:
            return {"ok": False, "rc": -1, "stdout": "", "stderr": str(e)}
        return {
            "ok": up.returncode == 0 and ug.returncode == 0,
            "rc": ug.returncode,
            "stdout": (up.stdout or "") + (ug.stdout or ""),
            "stderr": (up.stderr or "") + (ug.stderr or ""),
        }
    if pm == "dnf":
        cmd = nsenter(["dnf", "-y", "update"])
        try:
            cc = run(cmd, timeout=1800, trust_args=True)
        except CommandRejected as e:
            return {"ok": False, "rc": -1, "stdout": "", "stderr": str(e)}
        return _wrap_result(cc)
    return {
        "ok": False, "rc": -1, "stdout": "",
        "stderr": f"unsupported package manager: {pm}",
    }
