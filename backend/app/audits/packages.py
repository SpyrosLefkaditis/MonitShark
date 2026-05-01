"""Audit pending package updates. Distro-aware (apt vs dnf)."""
from __future__ import annotations

import hashlib
import time

from app.audits import register
from app.schemas import AuditReport, Finding
from app.util.nsenter import nsenter
from app.util.paths import OS_RELEASE
from app.util.sh import CommandRejected, run

_APT_DISTROS: frozenset[str] = frozenset({"debian", "ubuntu", "raspbian"})
_DNF_DISTROS: frozenset[str] = frozenset({"fedora", "rhel", "centos", "rocky", "almalinux"})

_PKG_NAMES_CAP = 20


def _fid(check: str, evidence: str) -> str:
    """Deterministic Finding.id keyed on check + evidence string."""
    return f"packages.{check}.{hashlib.sha1(evidence.encode()).hexdigest()[:10]}"


def _now() -> float:
    return time.time()


def _parse_os_release(text: str) -> dict[str, str]:
    """Parse a /etc/os-release-style file; values may be quoted."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        v = value.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        out[key.strip().lower()] = v
    return out


def _detect_pkg_manager() -> tuple[str | None, str | None, list[str]]:
    """Return (pkg_manager, id, id_like_tokens). pkg_manager is 'apt' | 'dnf' | None."""
    if not OS_RELEASE.exists():
        return None, None, []
    try:
        text = OS_RELEASE.read_text(errors="replace")
    except OSError:
        return None, None, []
    info = _parse_os_release(text)
    distro_id = info.get("id", "").lower()
    id_like = [t for t in info.get("id_like", "").lower().split() if t]
    candidates = {distro_id, *id_like}
    if candidates & _APT_DISTROS:
        return "apt", distro_id or None, id_like
    if candidates & _DNF_DISTROS:
        return "dnf", distro_id or None, id_like
    return None, distro_id or None, id_like


def _apt_check() -> tuple[list[str], list[str]]:
    """Return (security_pkgs, all_upgradable_pkgs). Best-effort; empty on failure."""
    cmd = nsenter(["apt", "list", "--upgradable"])
    try:
        cc = run(cmd, timeout=45)
    except CommandRejected:
        return [], []
    all_pkgs: list[str] = []
    security_pkgs: list[str] = []
    for raw in cc.stdout.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("listing"):
            continue
        # Format: "name/dist version arch [upgradable from: ...]"
        # Security packages live in "<dist>-security" repos and get tagged that way.
        name = line.split("/", 1)[0].strip()
        if not name:
            continue
        all_pkgs.append(name)
        low = line.lower()
        if "-security" in low or "[security]" in low:
            security_pkgs.append(name)
    return security_pkgs, all_pkgs


def _dnf_check() -> tuple[list[str], list[str]]:
    """Return (security_pkgs, all_upgradable_pkgs). Uses dnf updateinfo + check-update."""
    sec_cmd = nsenter(["dnf", "-q", "updateinfo", "list", "security"])
    security_pkgs: list[str] = []
    try:
        sec = run(sec_cmd, timeout=60)
        for raw in sec.stdout.splitlines():
            line = raw.strip()
            if not line:
                continue
            # `dnf updateinfo list security` rows: "<advisory> <severity> <package>"
            parts = line.split()
            if len(parts) >= 3:
                pkg = parts[-1]
                # Strip trailing arch (e.g. openssl-1.2.3-4.fc40.x86_64)
                security_pkgs.append(pkg)
    except CommandRejected:
        pass

    all_pkgs: list[str] = []
    chk_cmd = nsenter(["dnf", "-q", "check-update"])
    try:
        chk = run(chk_cmd, timeout=60)
    except CommandRejected:
        return security_pkgs, all_pkgs
    # rc 100 = updates available, 0 = none, anything else = error
    if chk.returncode in (0, 100):
        for raw in chk.stdout.splitlines():
            line = raw.strip()
            if not line or line.startswith("Obsoleting") or line.startswith("Last metadata"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                # First column is "<name>.<arch>" — strip the trailing arch.
                head = parts[0]
                name = head.rsplit(".", 1)[0] if "." in head else head
                all_pkgs.append(name)
    return security_pkgs, all_pkgs


@register("packages")
async def audit_packages() -> AuditReport:
    """Detect distro and report pending security/general updates."""
    findings: list[Finding] = []
    now = _now()

    pkg_mgr, distro_id, id_like = _detect_pkg_manager()
    if pkg_mgr is None:
        ev = f"unsupported:{distro_id}:{','.join(id_like)}"
        findings.append(Finding(
            id=_fid("unsupported_distro", ev),
            category="packages",
            severity="info",
            title="Distribution not supported by package audit",
            description=(
                "Beacon's package audit currently understands apt-based "
                "(Debian/Ubuntu/Raspbian) and dnf-based (Fedora/RHEL/CentOS/"
                "Rocky/AlmaLinux) systems. The detected distribution "
                f"({distro_id or 'unknown'}) is outside that set, so the audit "
                "cannot enumerate updates."
            ),
            evidence={"id": distro_id or "", "id_like": id_like},
            fix_id=None,
            status="open",
            created_at=now,
        ))
        return AuditReport(name="packages", findings=findings)

    if pkg_mgr == "apt":
        security_pkgs, all_pkgs = _apt_check()
    else:
        security_pkgs, all_pkgs = _dnf_check()

    sec_capped = security_pkgs[:_PKG_NAMES_CAP]
    all_capped = all_pkgs[:_PKG_NAMES_CAP]

    if security_pkgs:
        ev = f"security:{pkg_mgr}:{','.join(sec_capped)}"
        findings.append(Finding(
            id=_fid("security_updates_pending", ev),
            category="packages",
            severity="high",
            title=f"{len(security_pkgs)} security update(s) pending",
            description=(
                f"The host has {len(security_pkgs)} package(s) with security "
                "updates available. Apply them promptly: each pending advisory "
                "may include a fix for a known CVE. The `apply-fix` flow can "
                "run the appropriate distro upgrade command after confirmation."
            ),
            evidence={
                "package_manager": pkg_mgr,
                "count": len(security_pkgs),
                "packages": sec_capped,
                "truncated": len(security_pkgs) > _PKG_NAMES_CAP,
            },
            fix_id="packages.security_updates_pending",
            status="open",
            created_at=now,
        ))

    # Treat "all updates" as everything not already covered as security.
    non_sec = [p for p in all_pkgs if p not in set(security_pkgs)]
    if non_sec:
        ev = f"general:{pkg_mgr}:{len(non_sec)}"
        findings.append(Finding(
            id=_fid("general_updates_pending", ev),
            category="packages",
            severity="low",
            title=f"{len(non_sec)} general update(s) pending",
            description=(
                f"The host has {len(non_sec)} non-security package update(s) "
                "available. These are bug-fix and feature updates; applying "
                "them keeps the system aligned with the distro release."
            ),
            evidence={
                "package_manager": pkg_mgr,
                "count": len(non_sec),
                "packages": non_sec[:_PKG_NAMES_CAP],
                "truncated": len(non_sec) > _PKG_NAMES_CAP,
            },
            fix_id=None,
            status="open",
            created_at=now,
        ))

    return AuditReport(name="packages", findings=findings)
