"""LangGraph state machine.

Phase 6 graph (read-only, no confirmation gate yet):

    START → planner → router → {tool_exec | END}
    tool_exec → planner   (loop until LLM emits no tool calls)

`planner` is a Groq-backed ChatGroq with all read-only tools bound. `tool_exec`
runs every tool call from the most recent AI message and appends ToolMessages.
The router keeps looping until the LLM produces a final assistant turn with no
tool calls.

Phase 7 inserts a `confirmation_gate` node between `tool_exec` and the
destructive tools — using `langgraph.types.interrupt` to pause the graph and
surface a `confirm_request` frame over the WebSocket.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.schemas import AgentState
from app.agent.tools import TOOLS, TOOLS_BY_NAME, stringify_tool_output
from app.config import settings

logger = logging.getLogger("beacon.agent")


def _get_llm() -> ChatGroq:
    """Build the planner LLM. Lazy + per-request to keep things simple — the
    underlying httpx client is reused via groq SDK pooling."""
    # llama-3.3-70b is the highest-quality default but its free-tier TPM cap is
    # tight (12k). llama-3.1-8b-instant has 30k TPM and is more forgiving for
    # tool-call loops with chunky tool outputs. Switchable via GROQ_MODEL env.
    # streaming=False: Groq's tool-using responses sometimes arrive with empty
    # `.content` when streaming=True (the SDK's chunk reassembly skips the
    # final text in some structured-output paths). We use astream_events to
    # surface tool_call/tool_result frames; the final answer is sent in one
    # `final` frame after invoke completes. Simpler + more reliable than
    # token-by-token streaming for the hackathon demo.
    return ChatGroq(
        model=getattr(settings, "groq_model", None) or "llama-3.1-8b-instant",
        api_key=settings.groq_api_key,
        temperature=0,
        timeout=60,
        max_retries=2,
    ).bind_tools(TOOLS)


def _ensure_system_prompt(messages: list[BaseMessage]) -> list[BaseMessage]:
    if messages and isinstance(messages[0], SystemMessage):
        return messages
    return [SystemMessage(content=SYSTEM_PROMPT), *messages]


async def _planner(state: AgentState) -> dict[str, Any]:
    """Invoke the LLM. Returns a dict to merge into AgentState (langgraph
    accumulates `messages` via `add_messages`)."""
    msgs = _ensure_system_prompt(list(state["messages"]))
    llm = _get_llm()
    response = await llm.ainvoke(msgs)
    return {"messages": [response]}


async def _tool_exec(state: AgentState) -> dict[str, Any]:
    """Run every tool call from the last AI message and produce ToolMessages."""
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {"messages": []}
    out: list[BaseMessage] = []
    for tc in last.tool_calls:
        name = tc["name"]
        args = tc.get("args") or {}
        tool_call_id = tc.get("id") or name
        fn = TOOLS_BY_NAME.get(name)
        if fn is None:
            out.append(ToolMessage(
                content=stringify_tool_output({"error": f"unknown tool: {name}"}),
                tool_call_id=tool_call_id,
                name=name,
            ))
            continue
        try:
            result = await fn.ainvoke(args)
        except Exception as e:
            logger.exception("tool %s failed", name)
            result = {"error": repr(e)}
        out.append(ToolMessage(
            content=stringify_tool_output(result),
            tool_call_id=tool_call_id,
            name=name,
        ))
    return {"messages": out}


def _route(state: AgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tool_exec"
    return END


def _build() -> Any:
    g: StateGraph = StateGraph(AgentState)
    g.add_node("planner", _planner)
    g.add_node("tool_exec", _tool_exec)
    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", _route, {"tool_exec": "tool_exec", END: END})
    g.add_edge("tool_exec", "planner")
    return g


_compiled = None
_checkpointer: MemorySaver | None = None


def get_compiled() -> Any:
    """Compile-on-first-call pattern. MemorySaver (in-process) is fine for the
    hackathon — it gives the planner the conversation history within a single
    process lifetime; restarting the backend resets active threads."""
    global _compiled, _checkpointer
    if _compiled is None:
        _checkpointer = MemorySaver()
        _compiled = _build().compile(checkpointer=_checkpointer)
    return _compiled
