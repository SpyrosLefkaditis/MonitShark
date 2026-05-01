"""Tests for app.util.sh — the only sanctioned subprocess wrapper.

These guard the safety invariant: list args, shell=False, metachar rejection,
timeout enforcement.
"""
from __future__ import annotations

import subprocess

import pytest

from app.util.sh import CommandRejected, CompletedCommand, run


def test_run_echo_succeeds() -> None:
    result = run(["echo", "hi"])
    assert isinstance(result, CompletedCommand)
    assert result.ok is True
    assert result.returncode == 0
    assert "hi" in result.stdout


def test_run_rejects_semicolon() -> None:
    with pytest.raises(CommandRejected):
        run(["echo", "a; rm -rf /"])


def test_run_rejects_dollar() -> None:
    with pytest.raises(CommandRejected):
        run(["echo", "$HOME"])


def test_run_trust_args_allows_metachars() -> None:
    # trust_args=True bypasses the metachar regex; arg is passed straight through
    # to the child (still no shell, so no expansion). Just verify it doesn't raise.
    result = run(["echo", "x;y"], trust_args=True)
    assert result.ok is True
    assert "x;y" in result.stdout


def test_run_rejects_string_input() -> None:
    with pytest.raises(CommandRejected):
        run("echo hi")  # type: ignore[arg-type]


def test_run_rejects_empty_list() -> None:
    with pytest.raises(CommandRejected):
        run([])


def test_run_timeout_enforced() -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        run(["sleep", "10"], timeout=0.2)


def test_run_failing_command_returns_nonzero() -> None:
    result = run(["false"])
    assert result.returncode == 1
    assert result.ok is False
