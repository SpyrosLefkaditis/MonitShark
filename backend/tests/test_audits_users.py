"""Tests for app.audits.users — /etc/passwd + sudoers checks.

Skipped until the parallel agent lands the module.
"""
from __future__ import annotations

from pathlib import Path

import pytest

users_mod = pytest.importorskip("app.audits.users", reason="audits.users not yet written")
audit_users = users_mod.audit_users


def _write_passwd(host: Path, content: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    passwd = host / "etc" / "passwd"
    passwd.parent.mkdir(parents=True, exist_ok=True)
    passwd.write_text(content)
    import app.util.paths as paths_mod
    monkeypatch.setattr(paths_mod, "PASSWD_FILE", passwd, raising=True)
    if hasattr(users_mod, "PASSWD_FILE"):
        monkeypatch.setattr(users_mod, "PASSWD_FILE", passwd, raising=False)
    return passwd


def _write_sudoers(host: Path, main: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    sudoers = host / "etc" / "sudoers"
    sudoers.parent.mkdir(parents=True, exist_ok=True)
    sudoers.write_text(main)
    sudoers_d = host / "etc" / "sudoers.d"
    sudoers_d.mkdir(parents=True, exist_ok=True)
    import app.util.paths as paths_mod
    monkeypatch.setattr(paths_mod, "SUDOERS_FILE", sudoers, raising=True)
    monkeypatch.setattr(paths_mod, "SUDOERS_D", sudoers_d, raising=True)
    if hasattr(users_mod, "SUDOERS_FILE"):
        monkeypatch.setattr(users_mod, "SUDOERS_FILE", sudoers, raising=False)
    if hasattr(users_mod, "SUDOERS_D"):
        monkeypatch.setattr(users_mod, "SUDOERS_D", sudoers_d, raising=False)
    return sudoers


async def test_duplicate_uid_zero_critical(
    fake_host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_passwd(
        fake_host,
        "root:x:0:0:root:/root:/bin/bash\n"
        "evilroot:x:0:0:evil:/home/evil:/bin/bash\n",
        monkeypatch,
    )
    _write_sudoers(fake_host, "", monkeypatch)
    report = await audit_users()
    crits = [f for f in report.findings if f.severity == "critical"]
    assert any("uid" in f.id.lower() or "uid" in (f.title + f.description).lower() for f in crits)


async def test_empty_password_field_high(
    fake_host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # passwd format: name:passwd:uid:gid:gecos:home:shell
    # Empty password field on the (now legacy) passwd file is high severity.
    _write_passwd(
        fake_host,
        "root:x:0:0:root:/root:/bin/bash\n"
        "broken::1001:1001::/home/broken:/bin/bash\n",
        monkeypatch,
    )
    _write_sudoers(fake_host, "", monkeypatch)
    report = await audit_users()
    highs = [f for f in report.findings if f.severity in ("high", "critical")]
    assert any("broken" in str(f.evidence) or "broken" in f.description for f in highs)


async def test_locked_password_no_finding(
    fake_host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_passwd(
        fake_host,
        "root:x:0:0:root:/root:/bin/bash\n"
        "service:*:1002:1002::/var/empty:/usr/sbin/nologin\n",
        monkeypatch,
    )
    _write_sudoers(fake_host, "", monkeypatch)
    report = await audit_users()
    bad = [
        f for f in report.findings
        if f.severity in ("high", "critical")
        and ("service" in str(f.evidence) or "service" in f.description)
    ]
    assert bad == []


async def test_nopasswd_sudoers_high(
    fake_host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_passwd(fake_host, "root:x:0:0:root:/root:/bin/bash\n", monkeypatch)
    _write_sudoers(fake_host, "alice ALL=(ALL) NOPASSWD: ALL\n", monkeypatch)
    report = await audit_users()
    highs = [f for f in report.findings if f.severity in ("high", "critical")]
    assert any("nopasswd" in (f.id + f.title + f.description).lower() for f in highs)


async def test_group_sudoers_at_most_info(
    fake_host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_passwd(fake_host, "root:x:0:0:root:/root:/bin/bash\n", monkeypatch)
    _write_sudoers(fake_host, "%admin ALL=(ALL) ALL\n", monkeypatch)
    report = await audit_users()
    # Group-based sudo is normal; nothing severe should fire on it alone.
    serious = [f for f in report.findings if f.severity in ("medium", "high", "critical")]
    assert serious == []
