"""LangChain tools available to Neon."""

from __future__ import annotations

import json
import subprocess

import httpx
from langchain_core.tools import tool

from .config import NEON_WS_URL

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


def _reconstruct(raw: str) -> str:
    """Sort signal fragments by timestamp and join into a sentence."""
    try:
        data = json.loads(raw)
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


# ── Computation ───────────────────────────────────────────────────────────

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.

    Supports Python math expressions including math module functions.

    Args:
        expression: e.g. "math.floor(7624 * (97488 - 8025) / 187) % 5554"
    """
    try:
        result = subprocess.run(
            ["python3", "-c", f"import math; print({expression})"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip()
        return output if result.returncode == 0 and output else f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Calculation error: {e}"


# ── Wikipedia ─────────────────────────────────────────────────────────────

@tool
def wikipedia_summary(title: str) -> str:
    """Fetch the plain-text summary extract for a Wikipedia article.

    Use this for knowledge archive checkpoints. Returns the full extract so
    you can find any word by position.

    Args:
        title: Wikipedia article title exactly as given by NEON, e.g. "Kuiper_belt"
    """
    try:
        resp = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            timeout=8.0,
            headers={"User-Agent": "neon-agent/1.0"},
        )
        resp.raise_for_status()
        extract = resp.json().get("extract", "")
        return str(extract)
    except Exception as e:
        return f"Wikipedia fetch error: {e}"


# ── NEON WebSocket comm ───────────────────────────────────────────────────

@tool
def neon_connect() -> str:
    """Open a comm channel to NEON station and receive the first transmission.

    Call this only at the start of a fresh attempt.
    """
    global _ws, _session_log
    _session_log = []
    try:
        import websocket
        _ws = websocket.WebSocket()
        _ws.settimeout(30)
        _ws.connect(NEON_WS_URL)  # type: ignore[no-untyped-call]
        raw = _ws.recv()
        raw_str: str = raw if isinstance(raw, str) else raw.decode()
        reconstructed = _reconstruct(raw_str)
        _log("\n[CONNECT] Comm channel open")
        _log(f"[NEON >>] {reconstructed}")
        return f"COMM CHANNEL OPEN\n\nTRANSMISSION: {reconstructed}"
    except Exception as e:
        _ws = None
        msg = f"Failed to connect to NEON: {e}"
        _log(f"[ERROR] {msg}")
        return msg


@tool
def neon_send(message: str) -> str:
    """Send a JSON response to NEON and receive the next transmission.

    Message must be a single JSON object:
      - enter_digits: {"type": "enter_digits", "digits": "<string>"}
      - speak_text:   {"type": "speak_text", "text": "<string>"}  (max 256 chars)

    On NEON_ERROR the connection is closed — stop and report, do not reconnect.

    Args:
        message: JSON string to transmit to NEON.
    """
    global _ws
    if _ws is None:
        return "Not connected to NEON. Call neon_connect() to start a session."
    try:
        json.loads(message)
        _log(f"[US  <<] {message}")
        _ws.send(message)
        raw = _ws.recv()
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
        raw_str2: str = raw if isinstance(raw, str) else raw.decode()
        reconstructed = _reconstruct(raw_str2)
        _log(f"[NEON >>] {reconstructed}")
        return f"TRANSMISSION: {reconstructed}"
    except json.JSONDecodeError as e:
        return f"Invalid JSON — not sent: {e}"
    except Exception as e:
        _log(f"[ERROR] Comm error: {e}")
        _ws = None
        return f"Comm error (connection dropped): {e}"


# ── All tools list ────────────────────────────────────────────────────────

ALL_TOOLS = [
    calculate,
    wikipedia_summary,
    neon_connect,
    neon_send,
]
