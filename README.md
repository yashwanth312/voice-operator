<div align="center">

# 🎙️ Voice Operator

**Hold a key. Speak. Release. Done.**

Voice Operator is a personal, always-on Windows dictation tool — think Wispr Flow, but self-hosted.
Hold **Right Alt**, say what you want to type, and polished text appears in whatever window has focus.

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![STT](https://img.shields.io/badge/STT-ElevenLabs%20Scribe%20v2-orange?style=flat-square)
![LLM](https://img.shields.io/badge/cleanup-Groq%20Llama%203.3-purple?style=flat-square)

</div>

---

## What it does

```
You hold Right Alt  ──►  mic captures audio  ──►  ElevenLabs Scribe v2 (WebSocket, ~150 ms)
                                                           │
                                              live transcript appears on screen
                                                           │
                    You release Right Alt  ◄──  Groq cleans it up
                                                           │
                              cleaned text is pasted into the focused window  ──►  done
```

It's not a voice assistant. It doesn't listen for commands. It transcribes exactly what you say, cleans up the filler words and self-corrections, and pastes the result — wherever your cursor is.

---

## Features

| | What it does |
|---|---|
| **Hold-to-talk** | Right Alt held = recording. Release = paste. No mode switching. |
| **Live transcript overlay** | Real-time partial transcripts appear at the bottom of your screen while you speak. |
| **Smart cleanup** | Groq LLM strips filler words (`um`, `uh`, `like`), fixes punctuation, and resolves self-corrections (`"Tuesday — wait, Wednesday"` → `"Wednesday"`). |
| **App-aware tone** | Cleanup adapts to your focused window: casual for Slack/Discord, polished for Gmail/Outlook, terse for VS Code/terminal. |
| **Audio ducking** | System audio is ducked while you record so playback doesn't bleed into the mic. |
| **Tray icon** | Three-state EQ icon in the system tray — gray (idle), red (recording), amber (processing). |
| **Run at login** | One command installs a Startup folder shortcut for windowless background launch. |
| **Custom vocabulary** | Up to 100 domain-specific terms to bias the STT toward (names, jargon, product names). |

---

## Requirements

- **Windows 10 or 11**
- **Python 3.12+** (or use [uv](https://docs.astral.sh/uv/) — recommended)
- **ElevenLabs API key** — [elevenlabs.io](https://elevenlabs.io) (Pro plan recommended; free tier works with rate limits)
- **Groq API key** — [console.groq.com](https://console.groq.com) (free)

---

## Installation

### 1 — Clone and install dependencies

```powershell
git clone https://github.com/yashwanth312/voice-operator.git
cd voice-operator
uv sync
```

> Don't have `uv`? Install it: `pip install uv`

---

### 2 — Register pywin32 DLLs  *(one-time, Windows only)*

This step is required on every fresh machine. Without it the app crashes silently at startup.

```powershell
python .venv\Scripts\pywin32_postinstall.py -install
```

You only need to do this once per machine. If you recreate `.venv`, run it again.

---

### 3 — Create your config file

Copy the example config to the app data folder and fill in your API keys:

```powershell
# Create the folder
mkdir "$env:APPDATA\voice-operator" -Force

# Copy the template
copy config.example.yaml "$env:APPDATA\voice-operator\config.yaml"
```

Then open `%APPDATA%\voice-operator\config.yaml` in any editor and set your keys:

```yaml
elevenlabs_api_key: "sk_your_key_here"
groq_api_key:       "gsk_your_key_here"
```

---

### 4 — Run it

```powershell
uv run voice-operator
```

A sound-bar icon appears in your system tray. Hold **Right Alt** and speak.

---

## Configuration reference

Your config lives at `%APPDATA%\voice-operator\config.yaml`. All fields except the two API keys have sensible defaults.

<details>
<summary><strong>Click to expand full config reference</strong></summary>

```yaml
# ── Required ──────────────────────────────────────────────────────────────────

# ElevenLabs API key. Get yours at https://elevenlabs.io
elevenlabs_api_key: "sk_replace_me"

# Groq API key (free). Get yours at https://console.groq.com
groq_api_key: "gsk_replace_me"


# ── Speech-to-text ────────────────────────────────────────────────────────────

# Up to 100 domain-specific terms to bias Scribe toward.
# Useful for names, product names, jargon the model might mishear.
scribe_keyterms:
  - "ElevenLabs"
  - "your product name"


# ── Cleanup (LLM pass) ────────────────────────────────────────────────────────

# Groq model used for the cleanup pass.
# llama-3.3-70b-versatile is the recommended default.
cleanup_model: "llama-3.3-70b-versatile"

# Leave null to use the built-in cleanup prompt.
# Provide a string here to fully override it.
cleanup_system_prompt_override: null


# ── Hotkey ────────────────────────────────────────────────────────────────────

# The key to hold while speaking. Only "right_alt" is supported in v1.
hotkey: "right_alt"

# "hold" = record while the key is held. Only "hold" is supported in v1.
hold_or_toggle: "hold"


# ── Safety ────────────────────────────────────────────────────────────────────

# Auto-stop recording after this many seconds (runaway guard).
max_recording_seconds: 60
```

</details>

---

## Run at login

Make Voice Operator start automatically when you log in (runs as a background process — no terminal window):

```powershell
# Install autostart shortcut
uv run voice-operator --install-autostart

# Remove it
uv run voice-operator --uninstall-autostart
```

> **Note:** If you move the project folder or recreate `.venv`, re-run `--install-autostart` to update the shortcut path.

---

## How the cleanup works

The raw transcript from Scribe goes through a Groq LLM pass before being pasted. It applies these rules automatically:

- **Filler removal** — strips `um`, `uh`, `er`, `you know`, `like` (when used as filler)
- **Punctuation & capitalization** — adds sentence breaks and proper casing
- **Self-correction resolution** — `"meet Tuesday — wait, Wednesday"` → `"meet Wednesday"`
- **STT error correction** — uses context to fix homophone errors (`right` vs `write`)
- **App-aware tone:**

  | Focused app | Tone applied |
  |---|---|
  | Slack, Discord, Teams, iMessage | Casual, no greeting |
  | Gmail, Outlook | Polished, complete sentences |
  | VS Code, Cursor, terminal | Terse, technical — identifiers preserved verbatim |
  | Everything else | Neutral |

You can override the entire cleanup prompt via `cleanup_system_prompt_override` in your config.

---

## Logs

Logs are written to:

```
%APPDATA%\voice-operator\logs\voice-operator.log
```

You can also open the log folder from the tray: right-click the icon → **Open log folder**.

---

## Troubleshooting

<details>
<summary><strong>App crashes immediately / DLL load error for win32gui</strong></summary>

You skipped the pywin32 registration step. Run:

```powershell
python .venv\Scripts\pywin32_postinstall.py -install
```

</details>

<details>
<summary><strong>Right Alt isn't triggering dictation</strong></summary>

Check the log file (`%APPDATA%\voice-operator\logs\voice-operator.log`) for `"Hotkey listener started successfully"`. If you see it, the listener is running.

On some international keyboard layouts Right Alt generates `AltGr` instead of `Alt_R` — Voice Operator handles both. If it still doesn't work, check the log for `"Right Alt pressed"` to confirm the key is being detected.

</details>

<details>
<summary><strong>Transcription quality is poor</strong></summary>

Add domain-specific terms to `scribe_keyterms` in your config. You can include up to 100 terms — names, product names, acronyms, or jargon that Scribe tends to mishear.

</details>

<details>
<summary><strong>Cleanup is changing things I don't want changed</strong></summary>

You can fully replace the built-in cleanup prompt by setting `cleanup_system_prompt_override` in your config. Set it to a string containing your own system prompt. The active app name and window title are appended automatically.

</details>

<details>
<summary><strong>Audio from other apps is bleeding into the mic</strong></summary>

Voice Operator ducks system audio while recording. If ducking fails (you'll see a warning in the logs), it continues without it. Make sure no other app is holding an exclusive audio session lock.

</details>

---

## Running tests

```powershell
# Unit tests — no API keys needed
uv run pytest -m "not integration"

# Integration tests — hits live ElevenLabs + Groq
$env:ELEVENLABS_API_KEY="sk_..."; $env:GROQ_API_KEY="gsk_..."; uv run pytest -m integration
```

---

## Cost

Effectively **$0 marginal** for typical personal use:

| Service | Cost |
|---|---|
| ElevenLabs Scribe v2 | Covered by Pro plan's included hours |
| Groq cleanup (Llama 3.3 70B) | Free tier: 30 req/min, 6,000 req/day |

Free tier ElevenLabs works but has strict rate limits — you'll hit them quickly with heavy use.

---

## Architecture

```
voice_operator/
├── __main__.py       entry point — wires everything together
├── hotkey.py         global Right Alt listener (pynput)
├── session.py        one hold-to-talk cycle orchestration
├── audio.py          mic capture (sounddevice, 16 kHz PCM)
├── audio_ducking.py  system volume ducking (pycaw)
├── stt.py            ElevenLabs Scribe v2 WebSocket client
├── cleanup.py        Groq LLM cleanup pass
├── injector.py       clipboard paste into focused window
├── context.py        reads the active window title + app name
├── overlay.py        on-screen transcript overlay (tkinter)
├── tray.py           system tray icon (pystray + Pillow)
├── config.py         config loader (YAML from %APPDATA%)
└── autostart.py      Startup folder shortcut management
```
