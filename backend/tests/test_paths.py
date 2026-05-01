"""Tests for app.util.paths — path-allowlist resolution.

The allowlist is the only thing standing between a user-supplied path and a
read of /etc/shadow. These guard the rejection cases.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.util.paths import PathRejected, resolve_safe


def test_resolve_safe_allows_path_under_root(tmp_path: Path) -> None:
    log_root = tmp_path / "var" / "log"
    log_root.mkdir(parents=True)
    target = log_root / "auth.log"
    target.write_text("ok")
    resolved = resolve_safe(target, [log_root])
    assert resolved == target.resolve()


def test_resolve_safe_rejects_outside_root(tmp_path: Path) -> None:
    log_root = tmp_path / "var" / "log"
    log_root.mkdir(parents=True)
    etc = tmp_path / "etc"
    etc.mkdir()
    (etc / "passwd").write_text("root:x:0:0::/root:/bin/bash\n")
    with pytest.raises(PathRejected):
        resolve_safe(etc / "passwd", [log_root])


def test_resolve_safe_rejects_relative_escape(tmp_path: Path) -> None:
    log_root = tmp_path / "var" / "log"
    log_root.mkdir(parents=True)
    (tmp_path / "etc").mkdir()
    (tmp_path / "etc" / "passwd").write_text("root:x:0:0::/root:/bin/bash\n")
    # /var/log/../etc/passwd resolves to /etc/passwd, which is outside log_root.
    sneaky = log_root / ".." / "etc" / "passwd"
    with pytest.raises(PathRejected):
        resolve_safe(sneaky, [log_root])


def test_resolve_safe_expands_tilde(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Point HOME at tmp_path; ~ should expand to it before resolution.
    monkeypatch.setenv("HOME", str(tmp_path))
    sub = tmp_path / "logs"
    sub.mkdir()
    (sub / "auth.log").write_text("ok")
    resolved = resolve_safe("~/logs/auth.log", [sub])
    assert resolved == (sub / "auth.log").resolve()
