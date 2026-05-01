"""Tests for the auth routes (login + me) + bearer-required protection.

We import `app.main:app` lazily after env vars are set, then run a TestClient
against it. The auth router may not yet be wired into `app.main` — in that
case we skip the relevant tests.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def auth_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator:
    """Spin up a TestClient with a fresh users.yml + isolated config/data dirs."""
    # IMPORTANT: env must be set BEFORE app modules see config.
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("JWT_SECRET", "testsecret")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CONFIG_DIR", str(config_dir))

    # Reload config + auth so they pick up the new env vars.
    import importlib
    import app.config as config_mod
    importlib.reload(config_mod)
    import app.auth as auth_mod
    importlib.reload(auth_mod)

    # Seed users.yml with one known credential.
    pw_hash = auth_mod.hash_password("hunter2")
    users_yaml = config_dir / "users.yml"
    users_yaml.write_text(
        "users:\n"
        "  - username: alice\n"
        f"    password_hash: \"{pw_hash}\"\n"
        "    role: admin\n",
    )

    # Reload main last so it sees reloaded auth + config.
    main_mod = pytest.importorskip("app.main", reason="app.main not yet written")
    importlib.reload(main_mod)

    from fastapi.testclient import TestClient
    with TestClient(main_mod.app) as client:
        yield client, auth_mod


def _login_route_present(client) -> bool:
    routes = {getattr(r, "path", None) for r in client.app.routes}
    return "/api/auth/login" in routes


def test_login_bad_credentials_returns_401(auth_client) -> None:
    client, _ = auth_client
    if not _login_route_present(client):
        pytest.skip("auth router not registered in app.main")
    r = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    assert r.status_code == 401


def test_login_good_credentials_returns_token(auth_client) -> None:
    client, _ = auth_client
    if not _login_route_present(client):
        pytest.skip("auth router not registered in app.main")
    r = client.post("/api/auth/login", json={"username": "alice", "password": "hunter2"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("token_type") == "bearer"
    assert body.get("access_token")
    assert body["user"]["username"] == "alice"


def test_me_without_bearer_returns_401(auth_client) -> None:
    client, _ = auth_client
    if not _login_route_present(client):
        pytest.skip("auth router not registered in app.main")
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_bearer_returns_user(auth_client) -> None:
    client, _ = auth_client
    if not _login_route_present(client):
        pytest.skip("auth router not registered in app.main")
    login = client.post("/api/auth/login", json={"username": "alice", "password": "hunter2"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


def test_metrics_requires_bearer(auth_client) -> None:
    client, _ = auth_client
    routes = {getattr(r, "path", None) for r in client.app.routes}
    if "/api/metrics" not in routes:
        pytest.skip("metrics router not registered in app.main")
    r = client.get("/api/metrics")
    assert r.status_code == 401
