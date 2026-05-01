"""User management routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from app import users as users_mod
from app.auth import User, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUserIn(BaseModel):
    username: str
    fullname: str | None = None
    sudo: bool = False
    password: str | None = None
    ssh_public_key: str | None = None
    shell: str = "/bin/bash"


class AddSshKeyIn(BaseModel):
    public_key: str = Field(min_length=20, max_length=8192)


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=4, max_length=256)


@router.get("")
async def list_users(_user: Annotated[User, Depends(get_current_user)]) -> list[dict]:
    return users_mod.list_users()


@router.post("")
async def create_user(
    payload: CreateUserIn,
    _user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        return users_mod.create_user(**payload.model_dump(exclude_none=False))
    except users_mod.UserError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.get("/{username}/ssh-keys")
async def list_keys(
    username: Annotated[str, Path(min_length=1, max_length=64)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        return users_mod.list_ssh_keys(username)
    except users_mod.UserError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.post("/{username}/ssh-keys")
async def add_key(
    username: Annotated[str, Path(min_length=1, max_length=64)],
    payload: AddSshKeyIn,
    _user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        return users_mod.add_ssh_key(username, payload.public_key)
    except users_mod.UserError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/{username}/lock")
async def lock(
    username: Annotated[str, Path(min_length=1, max_length=64)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        return users_mod.lock_user(username)
    except users_mod.UserError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/{username}/unlock")
async def unlock(
    username: Annotated[str, Path(min_length=1, max_length=64)],
    _user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        return users_mod.unlock_user(username)
    except users_mod.UserError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/{username}/password")
async def set_password(
    username: Annotated[str, Path(min_length=1, max_length=64)],
    payload: SetPasswordIn,
    _user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        return users_mod.set_password(username, payload.password)
    except users_mod.UserError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
