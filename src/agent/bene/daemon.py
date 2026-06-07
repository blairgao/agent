"""Background heartbeat daemon for Bene."""

from __future__ import annotations

import os
import signal
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import (
    HEARTBEAT_INTERVAL_MINUTES,
    LOG_FILE,
    PID_FILE,
    QUIET_HOUR_END,
    QUIET_HOUR_START,
    USER_TZ,
    ensure_dirs,
)

# ── PID file management ───────────────────────────────────────────────────

def write_pid() -> None:
    """Write the current process PID to the PID file."""
    PID_FILE.write_text(str(os.getpid()))


def read_pid() -> int | None:
    """Read the daemon PID from the PID file, or return None if missing/invalid."""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (OSError, ValueError):
            pass
    return None


def clear_pid() -> None:
    """Remove the PID file if it exists."""
    if PID_FILE.exists():
        PID_FILE.unlink()


def is_running() -> bool:
    """Return True if the daemon process is alive."""
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)  # signal 0: just checks existence
        return True
    except (ProcessLookupError, PermissionError):
        clear_pid()
        return False


# ── Logging ───────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    ensure_dirs()
    now = datetime.now(ZoneInfo(USER_TZ)).strftime("%Y-%m-%d %H:%M:%S %Z")
    line = f"[{now}] {msg}\n"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)
    # Also print so it's visible when running in foreground
    print(line, end="", flush=True)


# ── Quiet hours ───────────────────────────────────────────────────────────

def _is_quiet_hour() -> bool:
    hour = datetime.now(ZoneInfo(USER_TZ)).hour
    if QUIET_HOUR_START <= QUIET_HOUR_END:
        return QUIET_HOUR_START <= hour < QUIET_HOUR_END
    # Wraps midnight (e.g. 23 to 8)
    return hour >= QUIET_HOUR_START or hour < QUIET_HOUR_END


# ── Heartbeat runner ──────────────────────────────────────────────────────

def run_heartbeat_once() -> str:
    """Run one heartbeat check and return the result."""
    # Import here to avoid circular / slow imports at daemon startup
    from .agent import make_agent, run_turn

    _log("Running heartbeat check...")
    agent = make_agent(mode="heartbeat")
    response = run_turn(
        agent,
        message="Run your heartbeat check now.",
        thread_id="heartbeat",
    )
    _log(f"Heartbeat result: {response[:200]}{'...' if len(response) > 200 else ''}")
    return response


# ── Main daemon loop ──────────────────────────────────────────────────────

def run_daemon_loop() -> None:
    """Blocking heartbeat loop — call this in the background process."""
    ensure_dirs()
    write_pid()
    _log(f"Bene daemon started (PID {os.getpid()}, interval {HEARTBEAT_INTERVAL_MINUTES}m)")

    def _handle_exit(signum, frame):
        _log(f"Received signal {signum}, shutting down.")
        clear_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_exit)
    signal.signal(signal.SIGINT, _handle_exit)

    while True:
        if not _is_quiet_hour():
            try:
                run_heartbeat_once()
            except Exception as e:
                _log(f"Heartbeat error: {e}")
        else:
            _log("Quiet hours — skipping heartbeat.")

        time.sleep(HEARTBEAT_INTERVAL_MINUTES * 60)


# ── CLI helpers ───────────────────────────────────────────────────────────

def start_daemon() -> str:
    """Fork and start the daemon in the background. Returns a status message."""
    if is_running():
        pid = read_pid()
        return f"Bene is already running (PID {pid})."

    ensure_dirs()

    pid = os.fork()
    if pid > 0:
        # Parent: return immediately
        return f"Bene daemon started in background (PID {pid})."
    else:
        # Child: become the daemon
        os.setsid()
        # Redirect stdin/stdout/stderr to /dev/null (except our log file)
        dev_null = open(os.devnull)
        os.dup2(dev_null.fileno(), sys.stdin.fileno())
        run_daemon_loop()
        sys.exit(0)


def stop_daemon() -> str:
    """Stop the running daemon. Returns a status message."""
    pid = read_pid()
    if not is_running():
        return "Bene daemon is not running."
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait briefly for it to die
        for _ in range(10):
            time.sleep(0.3)
            if not is_running():
                break
        clear_pid()
        return f"Bene daemon stopped (was PID {pid})."
    except Exception as e:
        return f"Error stopping daemon: {e}"


def daemon_status() -> str:
    """Return a human-readable status string."""
    if is_running():
        pid = read_pid()
        # Try to get uptime from log
        last_line = ""
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
            last_line = lines[-1] if lines else ""
        return (
            f"✅  Bene is running (PID {pid})\n"
            f"    Heartbeat every {HEARTBEAT_INTERVAL_MINUTES} min\n"
            f"    Log: {LOG_FILE}\n"
            f"    Last: {last_line}"
        )
    return "⬜  Bene daemon is not running."
