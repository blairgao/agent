"""Bene agent — backed by Claude via langchain.agents.create_agent."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from .config import MAX_TOKENS, MODEL
from .prompts import build_system_prompt
from .tools import ALL_TOOLS


def make_agent(mode: str = "chat"):
    """
    Create and return the compiled Bene agent graph.

    Args:
        mode: "chat" — interactive session with in-session memory (MemorySaver).
              "heartbeat" — stateless single-turn background check.
    """
    llm = ChatAnthropic(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=1,  # Claude's recommended default
    )

    system_prompt = build_system_prompt(mode=mode)

    # Chat mode gets an in-memory checkpointer so conversation history
    # persists across turns within the same session.
    checkpointer = MemorySaver() if mode == "chat" else None

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
    Send one message to Bene and return the final response text.

    Args:
        agent: Compiled agent graph from make_agent().
        message: User message to send.
        thread_id: Conversation thread ID for session continuity (chat mode only).
    """
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    messages = result.get("messages", [])
    # Return the last AI message content
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
