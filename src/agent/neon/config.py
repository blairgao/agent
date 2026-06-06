"""Configuration for the Neon agent."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

for _candidate in [Path(__file__).parents[3] / ".env", Path.home() / ".neon" / ".env"]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break

# Disable LangSmith tracing for neon — the shared .env may enable it but the
# LangSmith key is not configured, which causes blocking errors before any output.
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# ── Workspace ──────────────────────────────────────────────────────────────
_here = Path(__file__).parent
WORKSPACE_DIR: Path = _here / "workspace"
DATA_DIR: Path = Path(os.getenv("NEON_DATA_DIR", str(Path.home() / ".neon")))
MEMORY_DIR: Path = DATA_DIR / "memory"
LOGS_DIR: Path = DATA_DIR / "logs"
PID_FILE: Path = DATA_DIR / ".neon-daemon.pid"
LOG_FILE: Path = LOGS_DIR / "neon-daemon.log"

# ── Model ──────────────────────────────────────────────────────────────────
MODEL: str = os.getenv("NEON_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS: int = int(os.getenv("NEON_MAX_TOKENS", "8192"))

# ── Brave Search ──────────────────────────────────────────────────────────
BRAVE_API_KEY: str | None = os.getenv("BRAVE_API_KEY")

# ── NEON Station ──────────────────────────────────────────────────────────
NEON_WS_URL: str = os.getenv("NEON_WS_URL", "wss://neonhealth.software/agent-puzzle/challenge")
NEON_CODE: str | None = os.getenv("NEON_CODE")
ANTHROPIC_API_KEY: str | None = os.getenv("NEON_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

# ── Heartbeat ─────────────────────────────────────────────────────────────
HEARTBEAT_INTERVAL_MINUTES: int = int(os.getenv("NEON_HEARTBEAT_INTERVAL", "30"))
QUIET_HOUR_START: int = 23
QUIET_HOUR_END: int = 8

# ── User ──────────────────────────────────────────────────────────────────
USER_PHONE: str | None = os.getenv("NEON_USER_PHONE")
USER_NAME: str = os.getenv("NEON_USER_NAME", "Pilot")
USER_TZ: str = "America/Los_Angeles"


def ensure_dirs() -> None:
    """Create workspace dirs if they don't exist."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
