"""Memory management helpers for Neon."""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import MEMORY_DIR, USER_TZ, WORKSPACE_DIR


def _today() -> str:
    return datetime.now(ZoneInfo(USER_TZ)).strftime("%Y-%m-%d")


def _now_ts() -> str:
    return datetime.now(ZoneInfo(USER_TZ)).strftime("%H:%M")


# ── Daily memory log ──────────────────────────────────────────────────────

def append_daily_memory(content: str) -> str:
    """Append a timestamped entry to today's memory log file."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    today = _today()
    path = MEMORY_DIR / f"{today}.md"
    entry = f"\n## {_now_ts()}\n\n{content.strip()}\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(entry)
    return f"Wrote to memory/{today}.md"


def read_daily_memory(date: str | None = None) -> str:
    """Read a daily memory file (defaults to today)."""
    target = date or _today()
    path = MEMORY_DIR / f"{target}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"No memory file found for {target}."


# ── Long-term memory (MEMORY.md) ──────────────────────────────────────────

def read_long_term_memory() -> str:
    """Read the curated long-term MEMORY.md file."""
    path = WORKSPACE_DIR / "MEMORY.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "No long-term memory file yet."


def write_long_term_memory(content: str) -> str:
    """Overwrite MEMORY.md with new content."""
    path = WORKSPACE_DIR / "MEMORY.md"
    path.write_text(content, encoding="utf-8")
    return "Long-term memory (MEMORY.md) updated."


# ── Heartbeat state ───────────────────────────────────────────────────────

def get_heartbeat_state() -> dict:
    """Load heartbeat check timestamps."""
    path = MEMORY_DIR / "heartbeat-state.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"lastChecks": {"neon_comm": None}}


def update_heartbeat_state(checks: dict) -> str:
    """Update heartbeat state with new timestamps."""
    state = get_heartbeat_state()
    state["lastChecks"].update(checks)
    path = MEMORY_DIR / "heartbeat-state.json"
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return "Heartbeat state updated."


# ── Generic workspace file ops ────────────────────────────────────────────

def read_workspace_file(relative_path: str) -> str:
    """Read any file relative to the workspace root."""
    path = WORKSPACE_DIR / relative_path
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"File not found: {relative_path}"


def write_workspace_file(relative_path: str, content: str) -> str:
    """Write any file relative to the workspace root."""
    path = WORKSPACE_DIR / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Wrote {relative_path}"
