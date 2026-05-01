"""Tests for app.audits.permissions — world-writable + SUID checks.

Skipped until the parallel agent lands the module.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

perms_mod = pytest.importorskip("app.audits.permissions", reason="audits.permissions not yet written")
audit_permissions = perms_mod.audit_permissions


def _patch_host(host: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point HOST_ROOT at the fake host.

    The permissions module captures `_ETC`, `_BIN_DIRS`, `_SHADOW` from
    HOST_ROOT at import time, so we have to overwrite each derived constant.
    """
    import app.util.paths as paths_mod
    monkeypatch.setattr(paths_mod, "HOST_ROOT", host, raising=True)
    monkeypatch.setattr(perms_mod, "HOST_ROOT", host, raising=False)
    monkeypatch.setattr(perms_mod, "_ETC", host / "etc", raising=False)
    monkeypatch.setattr(perms_mod, "_SHADOW", host / "etc" / "shadow", raising=False)
    monkeypatch.setattr(
        perms_mod,
        "_BIN_DIRS",
        (host / "usr" / "bin", host / "usr" / "sbin"),
        raising=False,
    )


async def test_world_writable_file_in_etc_medium(
    fake_host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_host(fake_host, monkeypatch)
    target = fake_host / "etc" / "evil.conf"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("hi")
    os.chmod(target, 0o666)  # world-writable
    report = await audit_permissions()
    bad = [
        f for f in report.findings
        if f.severity in ("medium", "high", "critical")
        and "evil.conf" in str(f.evidence) + f.description
    ]
    assert bad, f"no finding for world-writable file; got {report.findings}"


async def test_world_readable_env_in_etc_high(
    fake_host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_host(fake_host, monkeypatch)
    target = fake_host / "etc" / ".env"
    target.write_text("SECRET=topsecret")
    os.chmod(target, 0o644)  # world-readable
    report = await audit_permissions()
    highs = [
        f for f in report.findings
        if f.severity in ("high", "critical")
        and ".env" in str(f.evidence) + f.description
    ]
    assert highs, f"no high finding for world-readable .env; got {report.findings}"


async def test_shadow_world_readable_high(
    fake_host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_host(fake_host, monkeypatch)
    shadow = fake_host / "etc" / "shadow"
    shadow.write_text("root:!:19000:0:99999:7:::\n")
    os.chmod(shadow, 0o644)
    report = await audit_permissions()
    highs = [
        f for f in report.findings
        if f.severity in ("high", "critical")
        and "shadow" in str(f.evidence) + f.description + f.title
    ]
    assert highs, f"no high finding for permissive /etc/shadow; got {report.findings}"


async def test_non_allowlisted_suid_root_medium(
    fake_host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_host(fake_host, monkeypatch)
    target = fake_host / "usr" / "bin" / "weird-binary"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"#!/bin/sh\necho hi\n")
    # Set SUID. We cannot reliably chown to root unless tests run as root.
    if os.geteuid() != 0:
        # Chown not strictly needed for the audit if it scans for setuid bit
        # regardless of owner; many implementations key on owner uid==0. Skip
        # if the audit specifically requires uid 0.
        pytest.skip("non-root: cannot chown SUID binary to root for the audit to flag")
    os.chown(target, 0, 0)
    os.chmod(target, 0o4755)  # SUID + rwxr-xr-x
    report = await audit_permissions()
    suid_findings = [
        f for f in report.findings
        if f.severity in ("medium", "high", "critical")
        and "weird-binary" in str(f.evidence) + f.description
    ]
    assert suid_findings, f"no finding for suspect SUID binary; got {report.findings}"
