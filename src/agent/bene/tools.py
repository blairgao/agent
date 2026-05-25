"""LangChain tools available to Bene."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from langchain_core.tools import tool

from .config import BRAVE_API_KEY, USER_TZ
from . import memory as mem


# ── Date / time ───────────────────────────────────────────────────────────

@tool
def get_current_time() -> str:
    """Return the current date and time in Blair's timezone (America/Los_Angeles)."""
    now = datetime.now(ZoneInfo(USER_TZ))
    return now.strftime("%A, %B %-d, %Y — %-I:%M %p %Z")


# ── Memory tools ──────────────────────────────────────────────────────────

@tool
def append_daily_memory(content: str) -> str:
    """
    Append a note to today's daily memory log.

    Use this whenever you learn something worth remembering for the next session,
    capture a decision, or want to log what you did.

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

    Use during heartbeats or when Blair asks you to update your long-term memory.
    Keep it curated: distilled insights, not raw logs.

    Args:
        content: The full new content for MEMORY.md.
    """
    return mem.write_long_term_memory(content)


@tool
def read_workspace_file(path: str) -> str:
    """
    Read a file from the agent workspace.

    Args:
        path: Path relative to the workspace root (e.g. "SOUL.md", "memory/2025-01-01.md").
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


@tool
def get_heartbeat_state() -> str:
    """Return the last heartbeat check timestamps as JSON."""
    state = mem.get_heartbeat_state()
    return json.dumps(state, indent=2)


@tool
def update_heartbeat_state(checks_json: str) -> str:
    """
    Update heartbeat check timestamps.

    Args:
        checks_json: JSON string mapping check names to Unix timestamps or ISO strings.
                     Example: '{"email": 1700000000, "imessage": 1700000000}'
    """
    checks = json.loads(checks_json)
    return mem.update_heartbeat_state(checks)


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

    Use for reading system state, checking git status, listing files, etc.
    Destructive commands (rm, delete, send) require Blair's explicit approval —
    ask before running them.

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


# ── iMessage (via imsg CLI) ───────────────────────────────────────────────

@tool
def send_imessage(to: str, message: str) -> str:
    """
    Send an iMessage to a phone number or handle.

    Use this to notify Blair of important things (urgent email, upcoming event, etc.).
    Only send if something genuinely matters — don't spam.

    Args:
        to: Phone number or Apple ID (e.g. "+14158108372").
        message: The message text to send.
    """
    try:
        result = subprocess.run(
            ["imsg", "send", to, message],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return f"iMessage sent to {to}."
        return f"Failed to send iMessage: {result.stderr.strip()}"
    except FileNotFoundError:
        return "imsg CLI not found. Install it or configure iMessage integration."
    except Exception as e:
        return f"Error sending iMessage: {e}"


@tool
def read_imessages(count: int = 10) -> str:
    """
    Read recent iMessages from the inbox.

    Args:
        count: Number of recent messages to fetch (default 10).
    """
    try:
        result = subprocess.run(
            ["imsg", "inbox", "--limit", str(count), "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip() or "No recent messages."
        return f"Error reading iMessages: {result.stderr.strip()}"
    except FileNotFoundError:
        return "imsg CLI not found. iMessage integration not available."
    except Exception as e:
        return f"Error: {e}"


# ── All tools list ────────────────────────────────────────────────────────

ALL_TOOLS = [
    get_current_time,
    append_daily_memory,
    read_daily_memory,
    read_long_term_memory,
    write_long_term_memory,
    read_workspace_file,
    write_workspace_file,
    get_heartbeat_state,
    update_heartbeat_state,
    web_search,
    run_shell,
    send_imessage,
    read_imessages,
]
