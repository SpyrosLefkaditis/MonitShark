"""Auth routes: POST /api/auth/login, GET /api/auth/me."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import (
    LoginIn,
    TokenOut,
    User,
    authenticate,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn) -> TokenOut:
    user = authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenOut(access_token=create_access_token(user), user=user)


@router.get("/me", response_model=User)
async def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user
