"""JWT auth + bcrypt password verification + users.yml loader.

Login flow:
  POST /api/auth/login {username, password}
    → look up user in users.yml, verify bcrypt hash
    → return {access_token, token_type: "bearer"}
  All other endpoints depend on `get_current_user` which validates the JWT
  in the Authorization header.

WebSocket auth: pass JWT as `?token=...` query param; use
`get_current_user_ws(websocket)` in the handler before accept().

If a user in users.yml has empty password_hash on startup, `bootstrap_users`
generates a random password, bcrypt-hashes it, writes back, and returns a
notice string for the entrypoint to print ONCE.
"""
from __future__ import annotations

import secrets
import string
import time
from dataclasses import dataclass
from typing import Annotated, Any

import jwt
import yaml
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.hash import bcrypt
from pydantic import BaseModel

from app.config import settings


class User(BaseModel):
    username: str
    role: str = "admin"


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


@dataclass
class _StoredUser:
    username: str
    password_hash: str
    role: str


def _load_users_raw() -> dict[str, Any]:
    p = settings.users_yaml_path
    if not p.exists():
        return {"users": []}
    data = yaml.safe_load(p.read_text()) or {}
    if not isinstance(data, dict):
        return {"users": []}
    return data


def _save_users_raw(data: dict[str, Any]) -> None:
    p = settings.users_yaml_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False))


def _list_users() -> list[_StoredUser]:
    raw = _load_users_raw()
    out: list[_StoredUser] = []
    for u in raw.get("users") or []:
        if not isinstance(u, dict):
            continue
        out.append(_StoredUser(
            username=str(u.get("username", "")),
            password_hash=str(u.get("password_hash", "") or ""),
            role=str(u.get("role", "admin")),
        ))
    return out


def _find_user(username: str) -> _StoredUser | None:
    return next((u for u in _list_users() if u.username == username), None)


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.verify(plain, hashed)
    except (ValueError, TypeError):
        return False


def hash_password(plain: str) -> str:
    return bcrypt.hash(plain)


def _gen_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def bootstrap_users() -> str | None:
    """If any user has empty password_hash, generate a random password, hash
    it, write back, and return a printable banner. None if no changes."""
    raw = _load_users_raw()
    users = raw.get("users") or []
    if not isinstance(users, list):
        return None
    changed = False
    notice_lines: list[str] = []
    for u in users:
        if not isinstance(u, dict):
            continue
        if not (u.get("password_hash") or "").strip():
            pwd = _gen_password()
            u["password_hash"] = hash_password(pwd)
            notice_lines.append(f"  username: {u.get('username')}  password: {pwd}")
            changed = True
    if changed:
        raw["users"] = users
        _save_users_raw(raw)
        return (
            "============================================================\n"
            "Beacon bootstrap admin credentials (printed ONCE — record now):\n"
            + "\n".join(notice_lines)
            + "\n============================================================"
        )
    return None


def authenticate(username: str, password: str) -> User | None:
    u = _find_user(username)
    if not u or not verify_password(password, u.password_hash):
        return None
    return User(username=u.username, role=u.role)


def create_access_token(user: User) -> str:
    now = int(time.time())
    payload = {
        "sub": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + settings.jwt_lifetime_s,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def _decode_token(token: str) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from e
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token claims")
    return User(username=sub, role=payload.get("role", "admin"))


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    return _decode_token(creds.credentials)


async def get_current_user_ws(websocket: WebSocket) -> User:
    """For WebSocket endpoints. Reads ?token= from query. Closes ws + raises on failure."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token query param")
    try:
        return _decode_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise
