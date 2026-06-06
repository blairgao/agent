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

# Module-level WebSocket connection and session log
_ws = None
_session_log: list[str] = []


def _log(entry: str) -> None:
    _session_log.append(entry)
    print(entry, flush=True)


def print_session_log() -> None:
    """Print the full session transcript. Called by the CLI after the agent finishes."""
    if not _session_log:
        return
    print("\n" + "=" * 60, flush=True)
    print("SESSION TRANSCRIPT", flush=True)
    print("=" * 60, flush=True)
    for line in _session_log:
        print(line, flush=True)
    print("=" * 60 + "\n", flush=True)


# ── Transmission reconstruction ───────────────────────────────────────────

def _reconstruct(raw: str) -> str:
    """
    Parse a list of signal fragments, sort by timestamp, join into a sentence.

    Each fragment: {"word": str, "timestamp": number}
    Falls back to returning raw if it's not a fragment list.
    """
    try:
        data = json.loads(raw)
        # Actual format: {"type": "...", "message": [{word, timestamp}, ...]}
        if isinstance(data, dict) and "message" in data:
            fragments = data["message"]
        elif isinstance(data, list):
            fragments = data
        else:
            return raw
        if fragments and "timestamp" in fragments[0]:
            fragments = sorted(fragments, key=lambda f: f["timestamp"])
            return " ".join(f["word"] for f in fragments)
    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
        pass
    return raw


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
        path: Path relative to the workspace root (e.g. "CREW.md", "MISSION.md").
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


# ── Computation ───────────────────────────────────────────────────────────

@tool
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression and return the result as a string.

    Use for computation checkpoints. Supports standard Python math expressions,
    including math module functions (sqrt, log, sin, cos, pi, etc.).

    Args:
        expression: A Python math expression, e.g. "2 ** 32" or "math.sqrt(144)".
    """
    try:
        result = subprocess.run(
            ["python3", "-c", f"import math; print({expression})"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip()
        if result.returncode != 0 or not output:
            return f"Error: {result.stderr.strip()}"
        return output
    except Exception as e:
        return f"Calculation error: {e}"


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
            lines.append(f"{r.get('title', '')}\n{r.get('url', '')}\n{r.get('description', '')}")
        return "\n\n".join(lines)

    except Exception as e:
        return f"Search error: {e}"


# ── NEON WebSocket comm ───────────────────────────────────────────────────

@tool
def neon_connect() -> str:
    """
    Open a comm channel to NEON station and receive the first transmission.

    Transmissions arrive as a JSON list of signal fragments sorted by timestamp.
    This tool reconstructs them into a readable sentence.
    Only call this at the start of a fresh attempt — not after an error. Fix
    the root cause of any error before reconnecting.
    """
    global _ws, _session_log
    _session_log = []  # reset log for new session
    try:
        import websocket  # websocket-client
        _ws = websocket.WebSocket()
        _ws.settimeout(30)
        _ws.connect(NEON_WS_URL)
        raw = _ws.recv()
        reconstructed = _reconstruct(raw)
        _log(f"\n[CONNECT] Comm channel open")
        _log(f"[NEON >>] {reconstructed}")
        return f"COMM CHANNEL OPEN\n\nTRANSMISSION: {reconstructed}"
    except Exception as e:
        _ws = None
        msg = f"Failed to connect to NEON: {e}"
        _log(f"[ERROR] {msg}")
        return msg


@tool
def neon_send(message: str) -> str:
    """
    Send a JSON response to NEON and receive the next transmission.

    The message must be a single JSON object with a 'type' field:
      - enter_digits: {"type": "enter_digits", "digits": "<string>"}
      - speak_text:   {"type": "speak_text", "text": "<string>"}  (max 256 chars)

    If NEON returns an error or timeout, the connection is closed automatically.
    Do NOT call neon_connect() to reconnect until the error is understood and fixed.

    Args:
        message: JSON string to transmit to NEON.
    """
    global _ws
    if _ws is None:
        return "Not connected to NEON. Call neon_connect() to start a session."
    try:
        json.loads(message)  # validate before sending
        _log(f"[US  <<] {message}")
        _ws.send(message)
        raw = _ws.recv()
        # Detect error/timeout responses — close and stop
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed.get("type") == "error":
                err_fragments = parsed.get("message", raw)
                if isinstance(err_fragments, list):
                    err_msg = " ".join(
                        f["word"] for f in sorted(err_fragments, key=lambda f: f["timestamp"])
                    )
                else:
                    err_msg = str(err_fragments)
                _log(f"[NEON >>] ERROR: {err_msg}")
                _log("[CLOSED] Connection closed due to error — diagnose before reconnecting")
                _ws.close()
                _ws = None
                return (
                    f"NEON_ERROR: {err_msg}\n"
                    "Connection closed. Diagnose the error before calling neon_connect()."
                )
        except (json.JSONDecodeError, TypeError):
            pass
        reconstructed = _reconstruct(raw)
        _log(f"[NEON >>] {reconstructed}")
        return f"TRANSMISSION: {reconstructed}"
    except json.JSONDecodeError as e:
        return f"Invalid JSON — not sent: {e}"
    except Exception as e:
        _log(f"[ERROR] Comm error: {e}")
        _ws = None
        return f"Comm error (connection dropped): {e}"


@tool
def neon_disconnect() -> str:
    """Explicitly close the comm channel to NEON station."""
    global _ws
    if _ws is None:
        return "No active connection."
    try:
        _ws.close()
        _ws = None
        _log("[CLOSED] Comm channel closed by co-pilot")
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
    calculate,
    run_shell,
    web_search,
    neon_connect,
    neon_send,
    neon_disconnect,
]
