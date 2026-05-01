"""Chat routes — REST one-shot + WebSocket streaming skeleton.

Phase 6 will replace the bodies with the LangGraph agent runner. For now
the handlers echo the input so the WS frame protocol shape and the
auth/disconnect plumbing are testable end-to-end.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.auth import User, get_current_user, get_current_user_ws
from app.schemas import ChatMessageIn, ChatMessageOut

log = logging.getLogger("beacon.chat")

router = APIRouter(prefix="/api", tags=["chat"])
ws_router = APIRouter(tags=["chat-ws"])

_STUB_PREFIX = "Agent not wired yet"
_TOKEN_DELAY_S = 0.05


@router.post("/chat", response_model=ChatMessageOut)
async def chat_oneshot(
    payload: ChatMessageIn,
    _user: Annotated[User, Depends(get_current_user)],
) -> ChatMessageOut:
    """Stub one-shot chat. Returns a canned response echoing the input."""
    return ChatMessageOut(
        thread_id=payload.thread_id or "stub-thread",
        text=f"{_STUB_PREFIX}. (Phase 6.) You said: {payload.message}",
    )


@ws_router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    """Streaming chat skeleton. Echoes user text as token frames + a final."""
    await get_current_user_ws(websocket)
    await websocket.accept()
    try:
        while True:
            frame = await websocket.receive_json()
            if not isinstance(frame, dict):
                continue
            kind = frame.get("type")
            if kind == "user":
                text = str(frame.get("text", ""))
                # Stream three token frames so the frontend can verify streaming
                # before Phase 6 wires the real agent.
                tokens = [
                    f"{_STUB_PREFIX} — ",
                    "you said: ",
                    text,
                ]
                final = "".join(tokens)
                for tok in tokens:
                    await websocket.send_json({"type": "token", "text": tok})
                    await asyncio.sleep(_TOKEN_DELAY_S)
                await websocket.send_json({"type": "final", "text": final})
            else:
                # Unknown frame types are ignored in the skeleton; Phase 6 will
                # handle "confirm" frames here.
                continue
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001 - surface the error frame, then close
        log.exception("chat ws handler error")
        try:
            await websocket.send_json({"type": "error", "message": "internal error"})
        except Exception:  # noqa: BLE001
            pass
