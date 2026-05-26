"""Configuration for the Bene agent."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (two levels up from this file's package)
for _candidate in [Path(__file__).parents[3] / ".env", Path.home() / ".bene" / ".env"]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break

# ── Workspace ──────────────────────────────────────────────────────────────
# Identity/personality files live inside the package (src/agent/bene/workspace/).
# Runtime data (memory logs, daemon pid, logs) lives in a writable data dir,
# defaulting to ~/.bene — override with BENE_DATA_DIR.
_here = Path(__file__).parent
WORKSPACE_DIR: Path = _here / "workspace"          # identity files (checked in)
DATA_DIR: Path = Path(os.getenv("BENE_DATA_DIR", str(Path.home() / ".bene")))
MEMORY_DIR: Path = DATA_DIR / "memory"
LOGS_DIR: Path = DATA_DIR / "logs"
PID_FILE: Path = DATA_DIR / ".bene-daemon.pid"
LOG_FILE: Path = LOGS_DIR / "bene-daemon.log"

# ── Model ──────────────────────────────────────────────────────────────────
MODEL: str = os.getenv("BENE_MODEL", "claude-sonnet-4-6")
MAX_TOKENS: int = int(os.getenv("BENE_MAX_TOKENS", "8192"))

# ── Brave Search ──────────────────────────────────────────────────────────
BRAVE_API_KEY: str | None = os.getenv("BRAVE_API_KEY")

# ── Heartbeat ─────────────────────────────────────────────────────────────
HEARTBEAT_INTERVAL_MINUTES: int = int(os.getenv("BENE_HEARTBEAT_INTERVAL", "30"))
# Quiet hours (local PT time, 24h)
QUIET_HOUR_START: int = 23
QUIET_HOUR_END: int = 8

# ── User ──────────────────────────────────────────────────────────────────
USER_PHONE: str | None = os.getenv("BENE_USER_PHONE")
USER_NAME: str = os.getenv("BENE_USER_NAME", "User")
USER_TZ: str = "America/Los_Angeles"

def ensure_dirs() -> None:
    """Create workspace dirs if they don't exist."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
