"""Bene CLI — your personal AI assistant, available at the terminal."""

from __future__ import annotations

import sys

import click

from .config import LOG_FILE, WORKSPACE_DIR, ensure_dirs

# ── Helpers ───────────────────────────────────────────────────────────────

def _print_bene(text: str) -> None:
    click.echo(click.style("Bene: ", fg="cyan", bold=True) + text)


def _print_error(text: str) -> None:
    click.echo(click.style("Error: ", fg="red", bold=True) + text, err=True)


# ── CLI root ──────────────────────────────────────────────────────────────

@click.group()
def main():
    r"""Bene — Blair's personal AI assistant.

    \b
    Commands:
      bene chat         Interactive chat session
      bene heartbeat    Run one heartbeat check now
      bene start        Start the background heartbeat daemon
      bene stop         Stop the background heartbeat daemon
      bene status       Show daemon status
      bene logs         Tail the daemon log
    """
    pass


# ── bene chat ─────────────────────────────────────────────────────────────

@main.command()
@click.option("--thread", default="main", show_default=True,
              help="Conversation thread ID (for session continuity).")
def chat(thread: str):
    """Start an interactive chat session with Bene."""
    ensure_dirs()

    click.echo(click.style("Bene", fg="cyan", bold=True) +
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
            _print_bene(response)
            click.echo()
        except KeyboardInterrupt:
            click.echo("\n(interrupted)")
        except Exception as e:
            _print_error(str(e))


# ── bene heartbeat ────────────────────────────────────────────────────────

@main.command()
def heartbeat():
    """Run one heartbeat check right now (foreground, shows output)."""
    ensure_dirs()
    click.echo(click.style("Running heartbeat check...\n", fg="yellow"))

    try:
        from .daemon import run_heartbeat_once
        result = run_heartbeat_once()
        _print_bene(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


# ── bene start ────────────────────────────────────────────────────────────

@main.command()
@click.option("--foreground", is_flag=True, default=False,
              help="Run in foreground instead of forking to background.")
def start(foreground: bool):
    """Start the Bene heartbeat daemon in the background."""
    ensure_dirs()

    if foreground:
        click.echo(click.style("Starting Bene daemon in foreground (Ctrl-C to stop)...\n",
                               fg="yellow"))
        from .daemon import run_daemon_loop
        run_daemon_loop()
    else:
        from .daemon import start_daemon
        msg = start_daemon()
        click.echo(click.style("🦾 ", fg="cyan") + msg)


# ── bene stop ─────────────────────────────────────────────────────────────

@main.command()
def stop():
    """Stop the running Bene heartbeat daemon."""
    from .daemon import stop_daemon
    msg = stop_daemon()
    click.echo(msg)


# ── bene status ───────────────────────────────────────────────────────────

@main.command()
def status():
    """Show daemon status and workspace info."""
    from .daemon import daemon_status
    click.echo(daemon_status())
    click.echo(click.style(f"\nWorkspace: {WORKSPACE_DIR}", fg="bright_black"))


# ── bene logs ─────────────────────────────────────────────────────────────

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
