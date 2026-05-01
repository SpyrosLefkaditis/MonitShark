"""Tests for app.audits.ssh — sshd_config parsing + finding emission."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.audits.ssh import audit_ssh_config


def _write_sshd(tmp_path: Path, content: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Write a synthetic sshd_config and patch SSHD_CONFIG to point at it."""
    cfg = tmp_path / "etc" / "ssh" / "sshd_config"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(content)
    # Patch in BOTH the module that owns the constant and the consumer that
    # imported it by-value at module load time.
    import app.util.paths as paths_mod
    import app.audits.ssh as ssh_mod
    monkeypatch.setattr(paths_mod, "SSHD_CONFIG", cfg, raising=True)
    monkeypatch.setattr(ssh_mod, "SSHD_CONFIG", cfg, raising=True)
    return cfg


async def test_empty_config_no_high_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_sshd(tmp_path, "", monkeypatch)
    report = await audit_ssh_config()
    high_or_worse = [f for f in report.findings if f.severity in ("high", "critical", "medium")]
    assert high_or_worse == []


async def test_permit_root_login_yes_high(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_sshd(tmp_path, "PermitRootLogin yes\n", monkeypatch)
    report = await audit_ssh_config()
    matched = [f for f in report.findings if f.id.startswith("ssh.permit_root_login")]
    assert len(matched) == 1
    assert matched[0].severity == "high"


async def test_password_authentication_yes_medium(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_sshd(tmp_path, "PasswordAuthentication yes\n", monkeypatch)
    report = await audit_ssh_config()
    matched = [f for f in report.findings if f.id.startswith("ssh.password_authentication")]
    assert len(matched) == 1
    assert matched[0].severity == "medium"


async def test_permit_empty_passwords_critical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_sshd(tmp_path, "PermitEmptyPasswords yes\n", monkeypatch)
    report = await audit_ssh_config()
    matched = [f for f in report.findings if f.id.startswith("ssh.permit_empty_passwords")]
    assert len(matched) == 1
    assert matched[0].severity == "critical"


async def test_comment_only_directive_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_sshd(tmp_path, "#PermitRootLogin yes\n", monkeypatch)
    report = await audit_ssh_config()
    matched = [f for f in report.findings if f.id.startswith("ssh.permit_root_login")]
    assert matched == []


async def test_last_occurrence_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_sshd(tmp_path, "PermitRootLogin yes\nPermitRootLogin no\n", monkeypatch)
    report = await audit_ssh_config()
    matched = [f for f in report.findings if f.id.startswith("ssh.permit_root_login")]
    assert matched == []


async def test_combined_three_issues_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = (
        "PermitRootLogin yes\n"
        "PasswordAuthentication yes\n"
        "PermitEmptyPasswords yes\n"
    )
    _write_sshd(tmp_path, cfg, monkeypatch)

    first = await audit_ssh_config()
    second = await audit_ssh_config()

    # Each of the three risky directives should produce one finding.
    ids_first = {f.id for f in first.findings}
    ids_second = {f.id for f in second.findings}
    assert ids_first == ids_second  # deterministic
    assert any(i.startswith("ssh.permit_root_login") for i in ids_first)
    assert any(i.startswith("ssh.password_authentication") for i in ids_first)
    assert any(i.startswith("ssh.permit_empty_passwords") for i in ids_first)
    # At least the three required findings present.
    assert len(ids_first) >= 3
