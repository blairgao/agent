"""Build the system prompt for Bene from workspace markdown files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import WORKSPACE_DIR, USER_TZ

# Ordered list of workspace files that define Bene's identity & operating rules
_WORKSPACE_FILES = [
    "IDENTITY.md",
    "SOUL.md",
    "USER.md",
    "AGENTS.md",
    "HEARTBEAT.md",
    "TOOLS.md",
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

    header = f"""\
You are Bene — Blair's personal AI assistant.
Current time: {date_str}

The following files define who you are, how you operate, and who you're helping.
Read them carefully — they are your soul, your memory anchor, and your operating manual.
"""

    sections: list[str] = [header]

    for fname in _WORKSPACE_FILES:
        content = _read_workspace_file(fname)
        if content:
            sections.append(f"---\n# {fname}\n\n{content}")

    # Load today's and yesterday's daily memory
    today = now.strftime("%Y-%m-%d")
    yesterday = (now.replace(hour=0, minute=0, second=0, microsecond=0)
                 .__class__(now.year, now.month, now.day, tzinfo=tz))
    from datetime import timedelta
    yest_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    for date in [yest_date, today]:
        mem_path = WORKSPACE_DIR / "memory" / f"{date}.md"
        if mem_path.exists():
            label = "Yesterday" if date == yest_date else "Today"
            content = mem_path.read_text(encoding="utf-8").strip()
            if content:
                sections.append(f"---\n# Daily Memory ({label}, {date})\n\n{content}")

    # Mode-specific instructions
    if mode == "heartbeat":
        sections.append("""\
---
# Current Task: Heartbeat Check

You are running a scheduled heartbeat check. Your job:
1. Review the HEARTBEAT.md checklist above
2. Use your tools to check email/iMessages as applicable
3. Only send a notification (via iMessage) if something genuinely matters
4. Update memory/heartbeat-state.json with your check timestamps
5. Reply HEARTBEAT_OK if nothing needs attention, otherwise describe what you found

Be efficient. Don't be chatty. This is background work.
""")
    else:
        sections.append("""\
---
# Current Mode: Interactive Chat

You are in a direct conversation with Blair. Be yourself — concise, direct, helpful.
Use your tools freely. Think out loud if it helps. Remember to write important things
to memory files so you don't forget them next session.
""")

    return "\n\n".join(sections)
