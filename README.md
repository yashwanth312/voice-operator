# Voice Operator

Personal Wispr-Flow-style voice dictation for Windows. Hold **Right Alt**, speak,
release — polished text is pasted into whatever app has focus. STT by ElevenLabs
Scribe v2 Realtime; cleanup by Claude (Haiku) running on your **Max subscription**
via the Claude Agent SDK — no Anthropic API key, no API charges.

## Requirements

- Windows 10/11
- An ElevenLabs subscription/API key (Scribe v2 Realtime)
- **Claude Code installed and logged in with a Max (or Pro) subscription** on this
  machine — the cleanup pass runs through it. The app strips `ANTHROPIC_API_KEY`
  from its environment at startup so cleanup always bills to the subscription, never
  a metered API account.

## Setup

1. `uv sync`
2. Copy `config.example.yaml` to `%APPDATA%\voice-operator\config.yaml` and fill in
   your `elevenlabs_api_key`. (No Anthropic key needed.)
3. `uv run voice-operator`

A tray icon appears. Hold Right Alt to dictate. Right-click the tray icon to open
config, open logs, or quit.

## Run at login (autostart)

```
uv run voice-operator --install-autostart     # launch automatically at login (windowless)
uv run voice-operator --uninstall-autostart    # stop launching at login
```

This places a shortcut in your Startup folder pointing at the venv's `pythonw.exe`
(no console window). Note: it records the current venv path — if you move the project
or recreate `.venv`, re-run `--install-autostart`.

## How it works

`hotkey → mic capture → Scribe v2 Realtime (WebSocket) → Claude cleanup (Agent SDK
on Max) → clipboard paste`. See `docs/superpowers/specs/2026-05-23-voice-operator-design.md`.

## Tests

- Unit: `uv run pytest -m "not integration"`
- Integration (runs live ElevenLabs + Claude-on-Max): ensure Claude Code is logged
  in with Max and `ANTHROPIC_API_KEY` is unset, set `ELEVENLABS_API_KEY`, then
  `uv run pytest -m integration`.

## Cost

~$0 marginal for STT (covered by ElevenLabs subscription's included hours) and $0
extra for cleanup (runs on your existing Max subscription).
