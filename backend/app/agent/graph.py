"""LangGraph state machine.

  START → planner → router → {tool_exec | END}
  tool_exec → planner    (loop until LLM emits no more tool calls)

`tool_exec` runs every tool call from the most recent AI message. Tools whose
name is in `DESTRUCTIVE_TOOLS` are gated by `langgraph.types.interrupt`: the
node pauses, the WS handler surfaces a `confirm_request` frame, the user
replies with `confirm`, and the handler resumes the graph with
`Command(resume={"decisions": {...}})`.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.schemas import AgentState
from app.agent.tools import TOOLS, TOOLS_BY_NAME, stringify_tool_output
from app.config import settings


# Throttle outgoing Groq calls so we don't burst into the per-minute / per-day
# rate limits. The free tier is ~12k TPM / 100k TPD on the 70b-versatile model;
# with ~50 bound tools each call costs 5-8k tokens. Spacing calls at 2.5s
# spreads steady usage to ~24 calls/min ceiling — safe headroom.
_MIN_PLANNER_INTERVAL_S = 2.5
_planner_gate = asyncio.Lock()
_last_planner_at = 0.0
logger = logging.getLogger("beacon.agent")

def _gather_destructive_names() -> set[str]:
    """Pull DESTRUCTIVE_NAMES from every tools_*.py that exposes it."""
    out: set[str] = set()
    for modname in ("tools_write", "tools_firewall", "tools_updates",
                    "tools_scripts", "tools_permissions", "tools_docker"):
        try:
            mod = __import__(f"app.agent.{modname}", fromlist=["DESTRUCTIVE_NAMES"])
            extra = getattr(mod, "DESTRUCTIVE_NAMES", None)
            if extra:
                out.update(extra)
        except ImportError:
            continue
    return out


DESTRUCTIVE_TOOLS: set[str] = _gather_destructive_names()


def _summarize_tool_call(name: str, args: dict) -> str:
    """Human-readable one-line description for the confirmation card."""
    if name == "create_user":
        u = args.get("username", "?")
        flags = []
        if args.get("sudo"): flags.append("sudo")
        if args.get("password"): flags.append("password")
        if args.get("ssh_public_key"): flags.append("SSH key")
        suffix = f" with {', '.join(flags)}" if flags else ""
        return f"Create Linux user '{u}'{suffix}"
    if name == "add_ssh_key":
        return f"Add an SSH public key to user '{args.get('username','?')}'"
    if name == "lock_user":
        return f"Lock user account '{args.get('username','?')}'"
    if name == "unlock_user":
        return f"Unlock user account '{args.get('username','?')}'"
    if name == "set_user_password":
        return f"Set password for user '{args.get('username','?')}'"
    if name == "service_action":
        return f"{args.get('action','?')} systemd service '{args.get('name','?')}'"
    if name == "apply_audit_fix":
        return f"Apply security fix '{args.get('fix_id','?')}'"
    return f"{name}({args})"


def _risk_of(name: str) -> str:
    high = {"create_user", "set_user_password", "lock_user"}
    med = {"add_ssh_key", "service_action", "apply_audit_fix", "unlock_user"}
    if name in high: return "high"
    if name in med: return "med"
    return "low"


def _get_llm() -> ChatGroq:
    # 70b-versatile gets us 12k TPM on free tier — needed because we bind ~50
    # tools and each schema costs ~100 tokens per request. The 8b-instant
    # model's 6k TPM limit is hit immediately.
    return ChatGroq(
        model=getattr(settings, "groq_model", None) or "llama-3.3-70b-versatile",
        api_key=settings.groq_api_key,
        temperature=0,
        timeout=60,
        max_retries=2,
    ).bind_tools(TOOLS)


def _ensure_system_prompt(messages: list[BaseMessage]) -> list[BaseMessage]:
    if messages and isinstance(messages[0], SystemMessage):
        return messages
    return [SystemMessage(content=SYSTEM_PROMPT), *messages]


async def _throttle() -> None:
    """Enforce a minimum interval between outgoing Groq calls."""
    global _last_planner_at
    async with _planner_gate:
        elapsed = time.monotonic() - _last_planner_at
        if elapsed < _MIN_PLANNER_INTERVAL_S:
            await asyncio.sleep(_MIN_PLANNER_INTERVAL_S - elapsed)
        _last_planner_at = time.monotonic()


def _format_rate_limit(err: Exception) -> str:
    s = str(err)
    if "tokens per day" in s.lower() or "TPD" in s:
        return ("Daily Groq token budget exhausted. The free tier resets at midnight UTC. "
                "Set GROQ_MODEL=llama-3.1-8b-instant in .env for higher daily limits, "
                "or upgrade to the dev tier.")
    if "tokens per minute" in s.lower() or "TPM" in s:
        return ("Per-minute Groq token limit hit — please wait ~30 seconds and try again, "
                "or shorten your question.")
    if "429" in s or "rate_limit" in s.lower():
        return "Groq rate limit hit. Please wait a moment and try again."
    return ""


async def _planner(state: AgentState) -> dict[str, Any]:
    msgs = _ensure_system_prompt(list(state["messages"]))
    llm = _get_llm()
    await _throttle()
    try:
        response = await llm.ainvoke(msgs)
    except Exception as e:
        friendly = _format_rate_limit(e)
        if friendly:
            logger.warning("planner rate-limited: %s", e)
            return {"messages": [AIMessage(content=friendly)]}
        raise
    return {"messages": [response]}


async def _tool_exec(state: AgentState) -> dict[str, Any]:
    """Run every tool call from the last AI message. Destructive tool calls are
    batched into a single `interrupt()` so the user approves them in one go."""
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {"messages": []}

    pending_destructive = [tc for tc in last.tool_calls if tc["name"] in DESTRUCTIVE_TOOLS]

    decisions: dict[str, str] = {}
    if pending_destructive:
        ops = []
        for tc in pending_destructive:
            ops.append({
                "tool_call_id": tc.get("id") or "",
                "tool": tc["name"],
                "args": tc.get("args") or {},
                "summary": _summarize_tool_call(tc["name"], tc.get("args") or {}),
                "risk": _risk_of(tc["name"]),
            })
        # interrupt() raises GraphInterrupt; the graph state is checkpointed and
        # astream yields a `__interrupt__` chunk to the WS handler. The handler
        # resumes via Command(resume={"decisions": {...}}).
        resume_value = interrupt({"pending_ops": ops})
        if isinstance(resume_value, dict) and isinstance(resume_value.get("decisions"), dict):
            decisions = {str(k): str(v) for k, v in resume_value["decisions"].items()}
        elif isinstance(resume_value, str):
            # Single decision applies to all (backward-compat / convenience).
            for op in ops:
                decisions[op["tool_call_id"]] = resume_value
        else:
            # Treat absence as denial.
            for op in ops:
                decisions[op["tool_call_id"]] = "deny"

    out: list[BaseMessage] = []
    for tc in last.tool_calls:
        name = tc["name"]
        args = tc.get("args") or {}
        tcid = tc.get("id") or name
        fn = TOOLS_BY_NAME.get(name)

        if name in DESTRUCTIVE_TOOLS:
            decision = decisions.get(tcid, "deny")
            if decision != "approve":
                out.append(ToolMessage(
                    content=stringify_tool_output({"denied": True, "reason": "user did not approve"}),
                    tool_call_id=tcid,
                    name=name,
                ))
                continue

        if fn is None:
            out.append(ToolMessage(
                content=stringify_tool_output({"error": f"unknown tool: {name}"}),
                tool_call_id=tcid,
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
            tool_call_id=tcid,
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
    global _compiled, _checkpointer
    if _compiled is None:
        _checkpointer = MemorySaver()
        _compiled = _build().compile(checkpointer=_checkpointer)
    return _compiled
