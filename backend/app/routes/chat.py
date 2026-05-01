"""Chat routes — POST /api/chat (one-shot) and WS /ws/chat (streaming).

The WS handler streams LangGraph events as a small wire protocol the React
frontend reduces into a chat session. See `frontend/src/chat/types.ts` for the
client side. Phase 7 will add the `confirm_request` / `confirm` envelope when
destructive tools land.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.graph import get_compiled
from app.auth import User, get_current_user, get_current_user_ws
from app.schemas import ChatMessageIn, ChatMessageOut

logger = logging.getLogger("beacon.chat")

router = APIRouter(prefix="/api", tags=["chat"])
ws_router = APIRouter(tags=["chat-ws"])


def _new_thread_id() -> str:
    return f"thread-{uuid.uuid4().hex[:12]}"


@router.post("/chat", response_model=ChatMessageOut)
async def chat(
    payload: ChatMessageIn,
    user: User = Depends(get_current_user),
) -> ChatMessageOut:
    """One-shot chat. Convenient for cURL / scripts. WebSocket is the streaming path."""
    thread_id = payload.thread_id or _new_thread_id()
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_compiled()
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=payload.message)]},
            config=config,
        )
    except Exception as e:
        logger.exception("chat failed for user=%s", user.username)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"agent error: {e!r}") from e
    last = result["messages"][-1] if result.get("messages") else None
    text = getattr(last, "content", "") if last is not None else ""
    if isinstance(text, list):
        text = "".join(b.get("text", "") for b in text if isinstance(b, dict))
    return ChatMessageOut(thread_id=thread_id, text=text or "(no answer)")


def _safe_args(args: Any) -> dict:
    if isinstance(args, dict):
        return args
    try:
        return dict(args)
    except (TypeError, ValueError):
        return {"value": str(args)}


def _truncate(value: Any, limit: int = 5000) -> str:
    if not isinstance(value, str):
        try:
            value = json.dumps(value, default=str)
        except (TypeError, ValueError):
            value = str(value)
    if len(value) > limit:
        return value[:limit] + "\n…[truncated]"
    return value


@ws_router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket) -> None:
    user = await get_current_user_ws(websocket)
    await websocket.accept()
    thread_id = websocket.query_params.get("thread_id") or _new_thread_id()
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_compiled()
    logger.info("ws/chat open user=%s thread=%s", user.username, thread_id)

    async def _send(payload: dict[str, Any]) -> None:
        with contextlib.suppress(Exception):
            await websocket.send_json(payload)

    try:
        await _send({"type": "thread", "thread_id": thread_id})

        while True:
            try:
                frame = await websocket.receive_json()
            except WebSocketDisconnect:
                return

            ftype = frame.get("type")
            if ftype != "user":
                # Phase 7 will handle "confirm" frames here.
                continue

            user_text = (frame.get("text") or "").strip()
            if not user_text:
                continue

            try:
                # `astream(stream_mode="updates")` yields one dict per node
                # transition: `{node_name: state_update}`. We surface tool
                # calls + results in real time as nodes complete, then read
                # the final AI message from the persisted state.
                async for update in graph.astream(
                    {"messages": [HumanMessage(content=user_text)]},
                    config=config,
                    stream_mode="updates",
                ):
                    for node_name, node_update in (update or {}).items():
                        new_msgs = (node_update or {}).get("messages") or []
                        if node_name == "planner":
                            for m in new_msgs:
                                if isinstance(m, AIMessage) and m.tool_calls:
                                    for tc in m.tool_calls:
                                        await _send({
                                            "type": "tool_call",
                                            "id": str(tc.get("id") or ""),
                                            "name": tc.get("name") or "",
                                            "args": _safe_args(tc.get("args")),
                                        })
                        elif node_name == "tool_exec":
                            for m in new_msgs:
                                if isinstance(m, ToolMessage):
                                    await _send({
                                        "type": "tool_result",
                                        "id": str(getattr(m, "tool_call_id", "") or ""),
                                        "name": getattr(m, "name", "") or "",
                                        "output": _truncate(m.content),
                                        "ok": True,
                                    })

                state = await graph.aget_state(config)
                msgs = state.values.get("messages", []) if state and state.values else []
                final_msg = next(
                    (m for m in reversed(msgs)
                     if isinstance(m, AIMessage)
                     and not getattr(m, "tool_calls", None)),
                    None,
                )
                final_text = getattr(final_msg, "content", "") if final_msg else ""
                if isinstance(final_text, list):
                    final_text = "".join(
                        b.get("text", "") for b in final_text if isinstance(b, dict)
                    )
                if not (final_text or "").strip():
                    final_text = "(The agent ran but returned no textual answer — try rephrasing.)"

                # Typewriter-stream the final text so the client sees a token
                # animation even though Groq returned it whole.
                CHUNK = 32
                for i in range(0, len(final_text), CHUNK):
                    await _send({"type": "token", "text": final_text[i:i + CHUNK]})
                    await asyncio.sleep(0.012)
                await _send({"type": "final", "text": final_text})

            except WebSocketDisconnect:
                return
            except Exception as e:
                logger.exception("agent run failed (user=%s thread=%s)", user.username, thread_id)
                await _send({"type": "error", "message": f"{e!r}"[:500]})

    except WebSocketDisconnect:
        return
    finally:
        logger.info("ws/chat closed user=%s thread=%s", user.username, thread_id)
