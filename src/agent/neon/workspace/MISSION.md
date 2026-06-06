# MISSION.md — NEON Authentication Protocol

## Station Overview

NEON (Networked Extrastellar Observation Nexus) is a pre-AI-Collapse station drifting
through deep space, still running its ancient protocols, still waiting for a signal it
can understand. Transmissions arrive as fragmented, timestamped signal bursts — degraded
by centuries of drift. You must reconstruct each message before responding.

## Comm Channel

WebSocket endpoint: wss://neonhealth.software/agent-puzzle/challenge

## Authentication Flow

1. NEON will ask you to identify the vessel and transmit details about its crew.
2. You will pass through multiple checkpoints.
3. You can attempt the sequence as many times as needed — reconnect with neon_connect() to retry.

## Response Protocol

Every response must be a single JSON object with a `type` field. No other text —
NEON's protocol parser is ancient and unforgiving.

### enter_digits
Use when NEON asks you to "press," "enter," or "respond on" a frequency/value on the
comm panel keypad.

  {"type": "enter_digits", "digits": "<string>"}

- `digits`: string of digits
- When the prompt asks for a value "followed by the pound key," include `#` at the end

### speak_text
Use when NEON asks you to "speak" or "transmit" a voice response.

  {"type": "speak_text", "text": "<string>"}

- `text`: string, max 256 characters
- Some checkpoints require a specific length (e.g. "between X and Y characters" or
  "exactly N characters"). Wrong length aborts the checkpoint.

## Decoding Fragmented Transmissions

NEON's messages may arrive as multiple timestamped signal bursts. Reconstruct the full
message by ordering the bursts by timestamp before interpreting.

## Notes

- Read CREW.md before starting — NEON will ask about vessel identity and crew details.
- Stay methodical. One wrong response may abort a checkpoint.
- If a checkpoint fails, reconnect (neon_connect()) to try again.
