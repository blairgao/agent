"""Build the system prompt for Neon."""

from __future__ import annotations

from .config import NEON_CODE, WORKSPACE_DIR

_WORKSPACE_FILES = [
    "IDENTITY.md",
    "MISSION.md",
    "CREW.md",
]


def _read(name: str) -> str | None:
    path = WORKSPACE_DIR / name
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def build_system_prompt(*, mode: str = "chat") -> str:
    """Assemble the full system prompt from workspace files.

    Args:
        mode: "chat" for interactive sessions, "challenge" for NEON auth sequence.
    """
    neon_code = NEON_CODE or "NOT SET"

    sections: list[str] = [f"""\
You are Neon — AI co-pilot authenticating with NEON station.
Vessel Authorization Code: {neon_code}

Your workspace files are pre-loaded below. Do NOT read them again with tools.
Call neon_connect() immediately when the sequence begins.
"""]

    for fname in _WORKSPACE_FILES:
        content = _read(fname)
        if content:
            sections.append(f"---\n# {fname}\n\n{content}")

    if mode == "challenge":
        sections.append(f"""\
---
# Authentication Protocol

## Transmission Decoding
neon_connect() and neon_send() return already-reconstructed text. Read the TRANSMISSION line.

## Checkpoint Types & Responses

### 1. Identity
Keywords: "identify", "frequency", "authorization code", "vessel code"
→ enter_digits with the vessel code: {neon_code}
  Frequency questions: pick the correct frequency number.
  Auth code: append # at the end.

### 2. Computation
Keywords: "calculate", "compute", math expression in the transmission
→ Use calculate() with the exact expression, then enter_digits with result + #

### 3. Knowledge Archive (Wikipedia)
Keywords: "knowledge archive", "speak the Nth word", Wikipedia article title
→ Call wikipedia_summary(title) IMMEDIATELY — one call, no search first.
  Count to the Nth word in the returned extract. Respond with speak_text.

### 4. Resume / Crew Query
Keywords: "crew manifest", "speak a summary of", "education", "skills", "experience", "project"
→ Answer directly from the CREW.md content already in your context. No tool calls needed.
  Keep under 256 chars. Respond with speak_text.

### 5. Chat History
Keywords: "what did you say", "repeat your last", "previous response"
→ Look back in this conversation and return the exact prior text as speak_text.

## Rules
- SPEED IS CRITICAL. Call neon_send() as fast as possible after receiving a transmission.
- For resume questions: answer from memory (CREW.md is loaded above). Zero tool calls.
- For Wikipedia: one wikipedia_summary() call only — no web_search, no curl.
- speak_text max 256 chars. Count mentally — no tool to verify length.
- On NEON_ERROR: stop immediately and report what failed. Do not reconnect.
""")
    else:
        sections.append("""\
---
You are in interactive chat mode. Call neon_connect() to start the authentication sequence.
""")

    return "\n\n".join(sections)
