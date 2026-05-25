# Voice Operator

Personal Wispr-Flow-style voice dictation for Windows. Hold **Right Alt**, speak,
release — polished text is pasted into whatever app has focus.

- **STT:** ElevenLabs Scribe v2 Realtime (WebSocket, ~150 ms latency)
- **Cleanup:** Groq (`llama-3.3-70b-versatile`) — removes fillers, fixes punctuation,
  resolves self-corrections, adapts tone to the active app
- **Injection:** clipboard paste into any focused window

## Requirements

- Windows 10/11
- [ElevenLabs](https://elevenlabs.io) API key (Pro plan recommended for included Scribe hours; free tier works with rate limits)
- [Groq](https://console.groq.com) API key (free)

## Setup

1. `uv sync`
2. Register the pywin32 DLLs (one-time, required on fresh Windows installs):
   ```
   python .venv\Scripts\pywin32_postinstall.py -install
   ```
3. Copy `config.example.yaml` to `%APPDATA%\voice-operator\config.yaml` and fill in
   your `elevenlabs_api_key` and `groq_api_key`.
4. `uv run voice-operator`

A tray icon appears. Hold **Right Alt** to dictate. Right-click the tray icon to quit.

## Run at login (autostart)

```
uv run voice-operator --install-autostart     # launch automatically at login (windowless)
uv run voice-operator --uninstall-autostart   # stop launching at login
```

Places a shortcut in your Startup folder using the venv's `pythonw.exe`. If you move
the project or recreate `.venv`, re-run `--install-autostart`.

## How it works

```
Right Alt held → mic capture → ElevenLabs Scribe v2 Realtime (WebSocket)
               → Groq cleanup (llama-3.3-70b-versatile) → clipboard paste
```

## Tests

```
# Unit tests (no API keys needed)
uv run pytest -m "not integration"

# Integration tests (hits live ElevenLabs + Groq)
ELEVENLABS_API_KEY=sk_... GROQ_API_KEY=gsk_... uv run pytest -m integration
```

## Cost

~$0 marginal — STT is covered by ElevenLabs Pro's included hours; cleanup runs on
Groq's free tier (30 req/min, 6,000 req/day).
