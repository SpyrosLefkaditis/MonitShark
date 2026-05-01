"""Tests for app.cron — python-crontab-backed read/write.

The cron module pins the spool root via module-level constants. We monkeypatch
those to a tmp_path so each test is hermetic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

cron_mod = pytest.importorskip("app.cron", reason="app.cron not yet written")


def _setup_spool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fake spool dir and patch the cron module to use it."""
    spool = tmp_path / "var" / "spool" / "cron"
    spool.mkdir(parents=True, exist_ok=True)
    system_crontab = tmp_path / "etc" / "crontab"
    system_crontab.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cron_mod, "_SPOOL_ROOT", spool, raising=True)
    monkeypatch.setattr(cron_mod, "_SYSTEM_CRONTAB", system_crontab, raising=True)
    return spool


async def test_list_all_returns_user_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    spool = _setup_spool(tmp_path, monkeypatch)
    user_tab = spool / "testuser"
    user_tab.write_text(
        "*/5 * * * * /usr/bin/true\n"
        "0 0 * * * /usr/bin/echo daily\n",
    )
    entries = cron_mod.list_all(user="testuser")
    assert len(entries) == 2
    ids = [e.id for e in entries]
    assert ids == ["testuser::0", "testuser::1"]


async def test_create_appends_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    spool = _setup_spool(tmp_path, monkeypatch)
    user_tab = spool / "testuser"
    user_tab.write_text(
        "*/5 * * * * /usr/bin/true\n"
        "0 0 * * * /usr/bin/echo daily\n",
    )
    from app.schemas import CronCreateIn
    payload = CronCreateIn(
        user="testuser",
        schedule="*/10 * * * *",
        command="/usr/bin/echo new",
        comment="added-by-test",
    )
    created = cron_mod.create(payload)
    assert created.user == "testuser"
    # File now has a 3rd line.
    after = cron_mod.list_all(user="testuser")
    assert len(after) == 3


async def test_delete_removes_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    spool = _setup_spool(tmp_path, monkeypatch)
    user_tab = spool / "testuser"
    user_tab.write_text(
        "*/5 * * * * /usr/bin/true\n"
        "0 0 * * * /usr/bin/echo daily\n",
    )
    assert cron_mod.delete("testuser::0") is True
    after = cron_mod.list_all(user="testuser")
    assert len(after) == 1


async def test_create_invalid_schedule_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    spool = _setup_spool(tmp_path, monkeypatch)
    (spool / "testuser").write_text("")
    from app.schemas import CronCreateIn
    payload = CronCreateIn(
        user="testuser",
        schedule="not-a-cron-schedule",
        command="/usr/bin/true",
    )
    with pytest.raises(Exception):  # noqa: B017 — python-crontab raises ValueError-ish
        cron_mod.create(payload)


async def test_invalid_username_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _setup_spool(tmp_path, monkeypatch)
    # username with shell metachars must never reach the filesystem.
    with pytest.raises((ValueError, cron_mod.CronError)):
        cron_mod.list_all(user="a; rm -rf /")
