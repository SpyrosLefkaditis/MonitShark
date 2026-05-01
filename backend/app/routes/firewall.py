"""UFW firewall routes. Bearer auth on every endpoint."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from app import firewall as fw
from app.auth import User, get_current_user

router = APIRouter(prefix="/api/firewall", tags=["firewall"])


class FirewallRuleIn(BaseModel):
    action: Literal["allow", "deny", "reject", "limit"]
    port: int | str = Field(..., description="numeric port 1-65535 or service name")
    proto: Literal["tcp", "udp"] | None = None
    source: str | None = None
    comment: str | None = Field(None, max_length=120)


class FirewallActionOut(BaseModel):
    ok: bool
    output: str


@router.get("/status")
async def get_status(_: Annotated[User, Depends(get_current_user)]) -> dict:
    """Return parsed ufw status (active flag, default policies, rules)."""
    try:
        return fw.status()
    except fw.FirewallError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.get("/rules")
async def list_rules(_: Annotated[User, Depends(get_current_user)]) -> list[dict]:
    """Return only the rule list."""
    try:
        return fw.list_rules()
    except fw.FirewallError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.post("/rules", response_model=FirewallActionOut, status_code=status.HTTP_201_CREATED)
async def add_rule(
    payload: FirewallRuleIn,
    _: Annotated[User, Depends(get_current_user)],
) -> FirewallActionOut:
    """Append a new UFW rule."""
    try:
        result = fw.add_rule(
            action=payload.action,
            port=payload.port,
            proto=payload.proto,
            source=payload.source,
            comment=payload.comment,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except fw.FirewallError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    return FirewallActionOut(**result)


@router.delete("/rules/{rule_number}", response_model=FirewallActionOut)
async def delete_rule(
    rule_number: Annotated[int, Path(ge=1, le=999)],
    _: Annotated[User, Depends(get_current_user)],
) -> FirewallActionOut:
    """Delete the rule at ``rule_number`` (1-based)."""
    try:
        result = fw.delete_rule(rule_number)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except fw.FirewallError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    return FirewallActionOut(**result)


@router.post("/enable", response_model=FirewallActionOut)
async def enable(_: Annotated[User, Depends(get_current_user)]) -> FirewallActionOut:
    """Activate UFW."""
    try:
        return FirewallActionOut(**fw.enable())
    except fw.FirewallError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.post("/disable", response_model=FirewallActionOut)
async def disable(_: Annotated[User, Depends(get_current_user)]) -> FirewallActionOut:
    """Deactivate UFW."""
    try:
        return FirewallActionOut(**fw.disable())
    except fw.FirewallError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
