"""Neon agent — backed by Claude via langchain.agents.create_agent."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from langgraph.checkpoint.memory import MemorySaver

from .config import ANTHROPIC_API_KEY, MAX_TOKENS, MODEL
from .prompts import build_system_prompt
from .tools import ALL_TOOLS


class _VerboseCallback(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name", "?")
        print(f"[AGENT] calling tool: {name}({input_str[:120]})", flush=True)

    def on_llm_start(self, serialized, prompts, **kwargs):
        print("[AGENT] thinking...", flush=True)


def make_agent(mode: str = "chat"):
    """
    Create and return the compiled Neon agent graph.

    Args:
        mode: "chat" — interactive session with in-session memory (MemorySaver).
              "challenge" — NEON authentication mode with mission context.
              "heartbeat" — stateless single-turn background check.
    """
    llm = ChatAnthropic(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=1,
        api_key=ANTHROPIC_API_KEY,
    )

    system_prompt = build_system_prompt(mode=mode)
    checkpointer = MemorySaver() if mode in ("chat", "challenge") else None

    agent = create_agent(
        model=llm,
        tools=ALL_TOOLS,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent


def run_turn(
    agent,
    message: str,
    thread_id: str = "default",
) -> str:
    """
    Send one message to Neon and return the final response text.

    Args:
        agent: Compiled agent graph from make_agent().
        message: User message to send.
        thread_id: Conversation thread ID for session continuity.
    """
    config = {"configurable": {"thread_id": thread_id}, "callbacks": [_VerboseCallback()]}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    messages = result.get("messages", [])
    for msg in reversed(messages):
        role = getattr(msg, "type", None) or getattr(msg, "role", None)
        if role in ("ai", "assistant"):
            content = msg.content
            if isinstance(content, list):
                parts = [
                    block["text"] if isinstance(block, dict) and block.get("type") == "text"
                    else str(block)
                    for block in content
                ]
                return "\n".join(parts)
            return str(content)
    return "(no response)"
