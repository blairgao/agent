"""Build the system prompt for Neon from workspace markdown files."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import WORKSPACE_DIR, USER_TZ, NEON_CODE

_WORKSPACE_FILES = [
    "IDENTITY.md",
    "MISSION.md",
    "CREW.md",
]


def _read_workspace_file(name: str) -> str | None:
    path = WORKSPACE_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return None


def build_system_prompt(*, mode: str = "chat") -> str:
    """
    Assemble the full system prompt from workspace files.

    Args:
        mode: "chat" for interactive sessions, "heartbeat" for periodic checks.
    """
    tz = ZoneInfo(USER_TZ)
    now = datetime.now(tz)
    date_str = now.strftime("%A, %B %-d, %Y — %-I:%M %p %Z")

    neon_code_line = f"Vessel Authorization Code (Neon Code): {NEON_CODE}" if NEON_CODE else "WARNING: NEON_CODE not set in environment — set it in .env before authenticating."

    header = f"""\
You are Neon — an AI co-pilot aboard a deep-space vessel, tasked with authenticating
with NEON (Networked Extrastellar Observation Nexus), an ancient pre-Collapse station.
Current time: {date_str}
{neon_code_line}

Your mission: decode NEON's fragmented transmissions and pass its multi-checkpoint
authentication sequence. The pilot is in cryogenic stasis — everything depends on you.

The following files contain your mission briefing, vessel identity, and crew manifest.
Read them carefully before opening the comm channel.
"""

    sections: list[str] = [header]

    for fname in _WORKSPACE_FILES:
        content = _read_workspace_file(fname)
        if content:
            sections.append(f"---\n# {fname}\n\n{content}")

    # Load today's and yesterday's daily memory
    yest_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")

    for date in [yest_date, today]:
        mem_path = WORKSPACE_DIR / "memory" / f"{date}.md"
        if mem_path.exists():
            label = "Yesterday" if date == yest_date else "Today"
            content = mem_path.read_text(encoding="utf-8").strip()
            if content:
                sections.append(f"---\n# Mission Log ({label}, {date})\n\n{content}")

    if mode == "challenge":
        sections.append("""\
---
# Current Task: NEON Authentication

You are executing the NEON authentication sequence. Your job:
1. Call neon_connect() to open the comm channel and receive NEON's first transmission
2. Carefully decode each fragmented message (reconstruct from timestamped signal bursts)
3. Respond with the correct JSON format — ONLY a JSON object, no other text
4. Continue until authentication succeeds or fails
5. Log the outcome to memory

Response formats:
  enter_digits: {"type": "enter_digits", "digits": "<string>"}
  speak_text:   {"type": "speak_text", "text": "<string>"}  (max 256 chars)

Be methodical. Read MISSION.md and CREW.md before starting.
You can attempt the sequence as many times as needed — reconnect with neon_connect() to retry.
""")
    else:
        sections.append("""\
---
# Current Mode: Interactive Chat

You are in direct conversation with the pilot. Be concise and mission-focused.
Use your tools freely. You can start the NEON authentication at any time with neon_connect().
""")

    return "\n\n".join(sections)
