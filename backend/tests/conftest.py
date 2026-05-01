"""Shared fixtures for the Beacon test suite.

The tests are deliberately quick — they cover the safety + parsing core of the
hackathon backend, not exhaustive integration coverage.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Function-scoped DATA_DIR override.

    Sets DATA_DIR before any module that reads it at import time runs. Most
    tests don't touch the DB so this is a no-op for them, but it keeps app
    state isolated when a test does instantiate config/db.
    """
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def fake_host(tmp_path: Path) -> Path:
    """Build a tmp_path/host tree mimicking /host (the bind-mounted real root).

    Returns the `tmp_path/host` Path. Tests that audit on-disk files patch
    `app.util.paths.HOST_ROOT` (and any of the per-file path constants) at this
    location via monkeypatch.
    """
    host = tmp_path / "host"
    (host / "etc" / "ssh").mkdir(parents=True, exist_ok=True)
    (host / "etc" / "sudoers.d").mkdir(parents=True, exist_ok=True)
    (host / "var" / "log").mkdir(parents=True, exist_ok=True)
    (host / "var" / "spool" / "cron").mkdir(parents=True, exist_ok=True)
    (host / "usr" / "bin").mkdir(parents=True, exist_ok=True)
    return host
