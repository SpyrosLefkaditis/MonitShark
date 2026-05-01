"""Chat routes — POST /api/chat (one-shot) and WS /ws/chat (streaming).

The WS handler runs the LangGraph agent and forwards a small wire protocol:

  server → client:
    {type: "thread", thread_id}
    {type: "tool_call", id, name, args}        # planner emitted a tool call
    {type: "tool_result", id, name, output, ok} # tool_exec produced a result
    {type: "confirm_request", request_id, pending_ops:[{tool_call_id,tool,args,summary,risk}]}
    {type: "token", text}                       # streamed final-answer chunk
    {type: "final", text}                       # full final answer
    {type: "error", message}

  client → server:
    {type: "user", text}
    {type: "confirm", request_id, decisions:{tool_call_id: "approve"|"deny"}}
    {type: "confirm", request_id, decision: "approve"|"deny"}  # legacy: applies to all
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
from langgraph.types import Command

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
    """One-shot chat. Cannot resolve interrupts — destructive tool calls will
    return as denied here. Use WS /ws/chat for the full flow."""
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


async def _send(ws: WebSocket, payload: dict[str, Any]) -> None:
    with contextlib.suppress(Exception):
        await ws.send_json(payload)


def _interrupt_payload_from_chunk(chunk: Any) -> dict | None:
    """Return the interrupt payload from a `__interrupt__` chunk, or None.
    Shape varies across langgraph versions; handle a few forms defensively."""
    if isinstance(chunk, dict):
        chunk = chunk.get("__interrupt__")
    if chunk is None:
        return None
    if isinstance(chunk, (list, tuple)) and chunk:
        first = chunk[0]
    else:
        first = chunk
    val = getattr(first, "value", None)
    if isinstance(val, dict):
        return val
    if isinstance(first, dict):
        return first
    return None


async def _stream_graph(ws: WebSocket, graph, config: dict, input_data: Any) -> dict | None:
    """Run the graph, forward `tool_call` / `tool_result` frames as nodes
    complete, and return any `__interrupt__` payload encountered (None if the
    graph ran to completion).
    """
    pending_interrupt: dict | None = None
    async for chunk in graph.astream(input_data, config=config, stream_mode="updates"):
        for node_name, node_update in (chunk or {}).items():
            if node_name == "__interrupt__":
                payload = _interrupt_payload_from_chunk(node_update)
                if payload is not None:
                    pending_interrupt = payload
                continue
            new_msgs = (node_update or {}).get("messages") or []
            if node_name == "planner":
                for m in new_msgs:
                    if isinstance(m, AIMessage) and m.tool_calls:
                        for tc in m.tool_calls:
                            await _send(ws, {
                                "type": "tool_call",
                                "id": str(tc.get("id") or ""),
                                "name": tc.get("name") or "",
                                "args": _safe_args(tc.get("args")),
                            })
            elif node_name == "tool_exec":
                for m in new_msgs:
                    if isinstance(m, ToolMessage):
                        await _send(ws, {
                            "type": "tool_result",
                            "id": str(getattr(m, "tool_call_id", "") or ""),
                            "name": getattr(m, "name", "") or "",
                            "output": _truncate(m.content),
                            "ok": True,
                        })
    return pending_interrupt


async def _emit_final(ws: WebSocket, graph, config: dict) -> None:
    """Pull the final AI message text from state and send it as token chunks
    + a `final` frame for the client's typewriter effect."""
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
        final_text = "".join(b.get("text", "") for b in final_text if isinstance(b, dict))
    if not (final_text or "").strip():
        final_text = "(The agent ran but returned no textual answer — try rephrasing.)"

    chunk_size = 32
    for i in range(0, len(final_text), chunk_size):
        await _send(ws, {"type": "token", "text": final_text[i:i + chunk_size]})
        await asyncio.sleep(0.012)
    await _send(ws, {"type": "final", "text": final_text})


def _decisions_from_confirm(frame: dict, pending_ops: list[dict]) -> dict[str, str]:
    """Map a `confirm` frame into {tool_call_id: 'approve'|'deny'}.
    Supports both the new `decisions: {...}` shape and the legacy
    `decision: 'approve'|'deny'` (applied to every pending op)."""
    decisions = frame.get("decisions")
    if isinstance(decisions, dict) and decisions:
        return {str(k): ("approve" if str(v).lower() == "approve" else "deny")
                for k, v in decisions.items()}
    legacy = frame.get("decision")
    if isinstance(legacy, str):
        verdict = "approve" if legacy.lower() == "approve" else "deny"
        return {op.get("tool_call_id") or "": verdict for op in pending_ops}
    return {op.get("tool_call_id") or "": "deny" for op in pending_ops}


@ws_router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket) -> None:
    user = await get_current_user_ws(websocket)
    await websocket.accept()
    thread_id = websocket.query_params.get("thread_id") or _new_thread_id()
    config: dict = {"configurable": {"thread_id": thread_id}}
    graph = get_compiled()
    logger.info("ws/chat open user=%s thread=%s", user.username, thread_id)

    try:
        await _send(websocket, {"type": "thread", "thread_id": thread_id})

        while True:
            try:
                frame = await websocket.receive_json()
            except WebSocketDisconnect:
                return
            ftype = frame.get("type")

            if ftype != "user":
                # Stray confirm without an active interrupt — ignore quietly.
                continue

            user_text = (frame.get("text") or "").strip()
            if not user_text:
                continue

            try:
                pending = await _stream_graph(
                    websocket, graph, config,
                    {"messages": [HumanMessage(content=user_text)]},
                )
                while pending is not None:
                    request_id = uuid.uuid4().hex
                    pending_ops = list(pending.get("pending_ops") or [])
                    await _send(websocket, {
                        "type": "confirm_request",
                        "request_id": request_id,
                        "pending_ops": pending_ops,
                    })
                    # Block on the next confirm frame for THIS request_id.
                    decisions: dict[str, str] | None = None
                    while decisions is None:
                        try:
                            cf = await websocket.receive_json()
                        except WebSocketDisconnect:
                            return
                        if cf.get("type") != "confirm":
                            continue
                        # Accept any request_id (single-flight per WS) but
                        # prefer matching ones if the client supplied it.
                        if cf.get("request_id") and cf.get("request_id") != request_id:
                            continue
                        decisions = _decisions_from_confirm(cf, pending_ops)
                    pending = await _stream_graph(
                        websocket, graph, config,
                        Command(resume={"decisions": decisions}),
                    )

                await _emit_final(websocket, graph, config)

            except WebSocketDisconnect:
                return
            except Exception as e:
                logger.exception("agent run failed (user=%s thread=%s)", user.username, thread_id)
                await _send(websocket, {"type": "error", "message": f"{e!r}"[:500]})

    except WebSocketDisconnect:
        return
    finally:
        logger.info("ws/chat closed user=%s thread=%s", user.username, thread_id)
