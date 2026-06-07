"""Neon CLI — AI co-pilot for the NEON station authentication sequence."""

from __future__ import annotations

import sys

import click

from .config import LOG_FILE, WORKSPACE_DIR, ensure_dirs

# ── Helpers ───────────────────────────────────────────────────────────────

def _print_neon(text: str) -> None:
    click.echo(click.style("Neon: ", fg="magenta", bold=True) + text)


def _print_error(text: str) -> None:
    click.echo(click.style("Error: ", fg="red", bold=True) + text, err=True)


# ── CLI root ──────────────────────────────────────────────────────────────

@click.group()
def main():
    r"""Neon — AI co-pilot for the NEON station authentication sequence.

    \b
    Commands:
      neon chat         Interactive chat session
      neon challenge    Execute the NEON authentication sequence
      neon heartbeat    Run one heartbeat check now
      neon start        Start the background heartbeat daemon
      neon stop         Stop the background heartbeat daemon
      neon status       Show daemon status
      neon logs         Tail the daemon log
    """
    pass


# ── neon chat ─────────────────────────────────────────────────────────────

@main.command()
@click.option("--thread", default="main", show_default=True,
              help="Conversation thread ID (for session continuity).")
def chat(thread: str):
    """Start an interactive chat session with Neon."""
    ensure_dirs()

    click.echo(click.style("Neon", fg="magenta", bold=True) +
               click.style(" is ready. Type 'exit' or Ctrl-C to quit.\n", fg="bright_black"))

    from .agent import make_agent, run_turn
    agent = make_agent(mode="chat")

    while True:
        try:
            user_input = click.prompt(
                click.style("You", fg="green", bold=True),
                prompt_suffix=": ",
            )
        except (EOFError, KeyboardInterrupt):
            click.echo("\nGoodbye.")
            break

        if user_input.strip().lower() in ("exit", "quit", "bye", ":q"):
            click.echo("Goodbye.")
            break

        if not user_input.strip():
            continue

        try:
            response = run_turn(agent, user_input, thread_id=thread)
            _print_neon(response)
            click.echo()
        except KeyboardInterrupt:
            click.echo("\n(interrupted)")
        except Exception as e:
            _print_error(str(e))


# ── neon challenge ────────────────────────────────────────────────────────

@main.command()
@click.option("--thread", default="challenge", show_default=True,
              help="Conversation thread ID.")
def challenge(thread: str):
    """Execute the NEON authentication sequence autonomously."""
    ensure_dirs()

    click.echo(
        click.style("\nINITIATING NEON AUTHENTICATION SEQUENCE\n", fg="magenta", bold=True) +
        click.style("Neon co-pilot engaging comm systems...\n", fg="bright_black")
    )

    from .agent import make_agent, run_turn
    from .tools import print_session_log

    agent = make_agent(mode="challenge")

    try:
        response = run_turn(
            agent,
            message=(
                "Begin the NEON authentication sequence. "
                "Your mission files are already loaded — call neon_connect() immediately. "
                "Work through every checkpoint until authentication succeeds. "
                "If you receive a NEON_ERROR, stop and report what failed."
            ),
            thread_id=thread,
        )
    except KeyboardInterrupt:
        click.echo("\n(interrupted)")
        response = "(interrupted by pilot)"
    except Exception as e:
        response = f"(agent error: {e})"

    print_session_log()
    click.echo()
    _print_neon(response)
    click.echo()


# ── neon heartbeat ────────────────────────────────────────────────────────

@main.command()
def heartbeat():
    """Run one heartbeat check right now (foreground, shows output)."""
    ensure_dirs()
    click.echo(click.style("Running heartbeat check...\n", fg="yellow"))

    try:
        from .daemon import run_heartbeat_once
        result = run_heartbeat_once()
        _print_neon(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


# ── neon start ────────────────────────────────────────────────────────────

@main.command()
@click.option("--foreground", is_flag=True, default=False,
              help="Run in foreground instead of forking to background.")
def start(foreground: bool):
    """Start the Neon heartbeat daemon in the background."""
    ensure_dirs()

    if foreground:
        click.echo(click.style("Starting Neon daemon in foreground (Ctrl-C to stop)...\n",
                               fg="yellow"))
        from .daemon import run_daemon_loop
        run_daemon_loop()
    else:
        from .daemon import start_daemon
        msg = start_daemon()
        click.echo(click.style(">> ", fg="magenta") + msg)


# ── neon stop ─────────────────────────────────────────────────────────────

@main.command()
def stop():
    """Stop the running Neon heartbeat daemon."""
    from .daemon import stop_daemon
    msg = stop_daemon()
    click.echo(msg)


# ── neon status ───────────────────────────────────────────────────────────

@main.command()
def status():
    """Show daemon status and workspace info."""
    from .daemon import daemon_status
    click.echo(daemon_status())
    click.echo(click.style(f"\nWorkspace: {WORKSPACE_DIR}", fg="bright_black"))


# ── neon logs ─────────────────────────────────────────────────────────────

@main.command()
@click.option("--lines", "-n", default=50, show_default=True,
              help="Number of lines to show.")
@click.option("--follow", "-f", is_flag=True, default=False,
              help="Follow the log (like tail -f).")
def logs(lines: int, follow: bool):
    """Show or follow the daemon log."""
    if not LOG_FILE.exists():
        click.echo("No log file yet. Start the daemon first.")
        return

    if follow:
        import subprocess
        subprocess.run(["tail", f"-n{lines}", "-f", str(LOG_FILE)])
    else:
        import subprocess
        subprocess.run(["tail", f"-n{lines}", str(LOG_FILE)])


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
