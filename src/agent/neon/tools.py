"""LangChain tools available to Neon."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from langchain_core.tools import tool

from .config import BRAVE_API_KEY, NEON_WS_URL, USER_TZ
from . import memory as mem

# Module-level WebSocket connection (persists across tool calls in a session)
_ws = None


# ── Date / time ───────────────────────────────────────────────────────────

@tool
def get_current_time() -> str:
    """Return the current date and time in the pilot's timezone (America/Los_Angeles)."""
    now = datetime.now(ZoneInfo(USER_TZ))
    return now.strftime("%A, %B %-d, %Y — %-I:%M %p %Z")


# ── Memory tools ──────────────────────────────────────────────────────────

@tool
def append_daily_memory(content: str) -> str:
    """
    Append a note to today's daily memory log.

    Args:
        content: The text to append to today's memory log.
    """
    return mem.append_daily_memory(content)


@tool
def read_daily_memory(date: str = "") -> str:
    """
    Read a daily memory log file.

    Args:
        date: Date string in YYYY-MM-DD format. Leave empty for today.
    """
    return mem.read_daily_memory(date or None)


@tool
def read_long_term_memory() -> str:
    """Read MEMORY.md — the curated long-term memory file."""
    return mem.read_long_term_memory()


@tool
def write_long_term_memory(content: str) -> str:
    """
    Overwrite MEMORY.md with updated long-term memory content.

    Args:
        content: The full new content for MEMORY.md.
    """
    return mem.write_long_term_memory(content)


@tool
def read_workspace_file(path: str) -> str:
    """
    Read a file from the agent workspace.

    Args:
        path: Path relative to the workspace root (e.g. "IDENTITY.md", "MISSION.md").
    """
    return mem.read_workspace_file(path)


@tool
def write_workspace_file(path: str, content: str) -> str:
    """
    Write a file to the agent workspace.

    Args:
        path: Path relative to the workspace root.
        content: Content to write.
    """
    return mem.write_workspace_file(path, content)


# ── Web search ────────────────────────────────────────────────────────────

@tool
def web_search(query: str, count: int = 5) -> str:
    """
    Search the web using Brave Search.

    Args:
        query: The search query.
        count: Number of results to return (default 5, max 10).
    """
    if not BRAVE_API_KEY:
        return "Brave Search API key not configured."

    count = min(count, 10)
    try:
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": count},
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("web", {}).get("results", [])
        if not results:
            return "No results found."

        lines = []
        for r in results:
            title = r.get("title", "")
            url = r.get("url", "")
            desc = r.get("description", "")
            lines.append(f"**{title}**\n{url}\n{desc}")
        return "\n\n".join(lines)

    except Exception as e:
        return f"Search error: {e}"


# ── Shell ─────────────────────────────────────────────────────────────────

@tool
def run_shell(command: str) -> str:
    """
    Run a shell command and return its output.

    Args:
        command: The shell command to execute.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Error: {e}"


# ── NEON WebSocket comm ───────────────────────────────────────────────────

@tool
def neon_connect() -> str:
    """
    Open a comm channel to NEON station and receive the first transmission.

    Call this at the start of an authentication attempt. Returns the first
    message received from NEON after connecting.
    """
    global _ws
    try:
        import websocket  # websocket-client
        _ws = websocket.WebSocket()
        _ws.connect(NEON_WS_URL)
        # Receive the opening transmission from NEON
        msg = _ws.recv()
        return f"COMM CHANNEL OPEN\n\n{msg}"
    except Exception as e:
        return f"Failed to connect to NEON: {e}"


@tool
def neon_send(message: str) -> str:
    """
    Send a JSON response to NEON and receive the next transmission.

    The message must be a single JSON object with a 'type' field:
      - enter_digits: {"type": "enter_digits", "digits": "<string>"}
      - speak_text:   {"type": "speak_text", "text": "<string>"}

    NEON's protocol parser is ancient and unforgiving — no extra text, only valid JSON.

    Args:
        message: JSON string to transmit to NEON.
    """
    global _ws
    if _ws is None:
        return "Not connected to NEON. Call neon_connect() first."
    try:
        # Validate it's JSON before sending
        json.loads(message)
        _ws.send(message)
        response = _ws.recv()
        return response
    except json.JSONDecodeError as e:
        return f"Invalid JSON — NEON would reject this: {e}"
    except Exception as e:
        _ws = None
        return f"Comm error (connection reset): {e}"


@tool
def neon_disconnect() -> str:
    """Close the comm channel to NEON station."""
    global _ws
    if _ws is None:
        return "No active connection."
    try:
        _ws.close()
        _ws = None
        return "Comm channel closed."
    except Exception as e:
        _ws = None
        return f"Error closing connection: {e}"


# ── All tools list ────────────────────────────────────────────────────────

ALL_TOOLS = [
    get_current_time,
    append_daily_memory,
    read_daily_memory,
    read_long_term_memory,
    write_long_term_memory,
    read_workspace_file,
    write_workspace_file,
    web_search,
    run_shell,
    neon_connect,
    neon_send,
    neon_disconnect,
]
