# Bene

Blair's personal AI assistant. It's built on [LangGraph](https://github.com/langchain-ai/langgraph) and Claude.

Bene monitors email and iMessages, answers questions, searches the web, manages memory across sessions, runs periodic heartbeat checks, and many more.

## Installation

```bash
uv venv
uv pip install -e .
```

Then copy `.env.example` to `.env` and fill in your API key:

```bash
cp .env.example .env
```

## Usage

```bash
bene chat              # start an interactive chat session
bene heartbeat         # run one proactive check right now
bene start             # start the background heartbeat daemon (every 30 min)
bene stop              # stop the daemon
bene status            # show daemon status
bene logs -f           # follow the daemon log
```

## Workspace files

Bene reads these markdown files at startup to know who he is and who he is helping:

| File | Purpose |
|---|---|
| `IDENTITY.md` | Name, vibe, eyc |
| `SOUL.md` | Personality, values, Blair-specific rules |
| `USER.md` | About Blair |
| `AGENTS.md` | Operating instructions |
| `HEARTBEAT.md` | What to check during heartbeat runs |
| `TOOLS.md` | Local tool notes (camera names, SSH hosts, etc.) |
| `memory/YYYY-MM-DD.md` | Daily memory logs |
| `MEMORY.md` | Long-term curated memory |

Edit any of these files to change Bene's behaviour. For anyone new setting up the agent:

```bash
  cd src/agent/bene/workspace
  for f in *.example; do cp "$f" "${f%.example}"; done
```

## Project structure

```
src/agent/bene/
  config.py    — settings and paths
  prompts.py   — builds system prompt from workspace files
  memory.py    — memory read/write helpers
  tools.py     — list of available tools
  agent.py     — creating agent
  daemon.py    — background heartbeat daemon (start/stop/status)
  cli.py       — Click CLI entry point
```
