# Voice Operator — Design

**Date:** 2026-05-23
**Status:** Approved, ready for implementation planning
**Author:** Yash (designed with Claude)

## 1. Problem

I want a Wispr-Flow-style voice dictation tool on Windows for personal use. Press and hold a global hotkey, speak, release — and have polished text appear in whichever app currently has focus. The tool must clean up fillers, fix punctuation, resolve self-corrections, and lightly adapt tone to the active app. It must use ElevenLabs as the speech-to-text engine, because I already have an ElevenLabs Pro subscription.

The deliverable is a personal tool — not a product. No multi-user, no auth, no GUI for settings, no telemetry.

## 2. Decisions (locked during brainstorming)

| Axis | Choice |
|---|---|
| Scope | System-wide on Windows (works in any focused field) |
| STT engine | ElevenLabs Scribe v2 Realtime (WebSocket, ~150 ms latency) |
| Cleanup engine | Claude Haiku 4.5 via Anthropic SDK |
| Tech stack | Python daemon with system tray and floating overlay |
| Trigger | Press-and-hold Right Alt |
| Cleanup level | Wispr Flow parity — filler removal, punctuation, backtracking resolution, light tone adaptation by active app |
| Text injection | Clipboard save → SetClipboardText → SendInput Ctrl+V → restore clipboard |
| Out of scope (v1) | Command Mode, personal dictionary auto-learning, settings GUI, cross-platform, multi-language switching, VAD-based auto-stop |

## 3. High-level pipeline

```
                 ┌──────────────────────────────────────────────┐
                 │ Python daemon (tray icon, always running)    │
                 └──────────────────────────────────────────────┘
                                       │
   Right Alt down  ──────────────────► │ hotkey listener (pynput)
                                       │
                                       ▼
   ┌──────────────────────────────────────────────────────────┐
   │ START                                                    │
   │  1. sounddevice opens 16-kHz mono PCM mic stream         │
   │  2. open WebSocket to wss://api.elevenlabs.io/v1/        │
   │       speech-to-text/realtime  (Scribe v2 Realtime)      │
   │  3. show floating overlay (always-on-top, live partials) │
   │  4. capture foreground window name (context for cleanup) │
   │  5. duck other audio outputs by ~70%                     │
   └──────────────────────────────────────────────────────────┘
                                       │
                  audio chunks ────────►  Scribe v2 (150 ms RT)
                                       │
                  partial transcripts ◄──  → render in overlay
                                       │
   Right Alt up   ──────────────────► │  send "commit" → final transcript
                                       │
                                       ▼
   ┌──────────────────────────────────────────────────────────┐
   │ CLEANUP                                                  │
   │  • call Claude Haiku 4.5 with raw transcript +           │
   │    app context (e.g. "user is in Slack")                 │
   │  • system prompt: strip fillers, fix punctuation,        │
   │    resolve backtracking, light tone adapt, NEVER         │
   │    change meaning                                        │
   │  • abort if >1500 ms; fall back to raw transcript        │
   └──────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌──────────────────────────────────────────────────────────┐
   │ INJECT                                                   │
   │  • save current clipboard                                │
   │  • SetClipboardText(cleaned)                             │
   │  • SendInput Ctrl+V                                      │
   │  • restore original clipboard ~150 ms later              │
   └──────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                  dismiss overlay, restore audio levels
```

**Why this shape:**
- **Streaming STT, batched cleanup.** Cleanup only runs once on the final transcript. Streaming into the LLM would be noisier and slower; Haiku's ~400 ms round-trip is acceptable.
- **Clipboard-paste injection** (with save/restore) is the most reliable method across native Win32, Electron (VS Code, Slack, Discord), browsers, and Office. UIA is cleaner in theory but breaks on enough apps that hybrid logic isn't worth the bug surface for v1.
- **Foreground window name** is captured before the LLM call so cleanup can lightly adapt tone.

## 4. Module structure

```
voice_operator/
├── pyproject.toml              # uv-managed project
├── config.example.yaml         # user copies → config.yaml
├── README.md
├── voice_operator/
│   ├── __main__.py             # entrypoint: load config, start tray + hotkey listener, run event loop
│   ├── config.py               # YAML loader; api keys, hotkey, custom dictionary (Scribe keyterms), LLM prompt overrides
│   ├── hotkey.py               # pynput global Right-Alt press-and-hold detection; emits start/stop events
│   ├── audio.py                # sounddevice 16kHz mono PCM capture, ring-buffered chunks
│   ├── stt.py                  # async WebSocket client for Scribe v2 Realtime; yields partial + final transcripts
│   ├── cleanup.py              # Anthropic SDK call to Claude Haiku 4.5 with prompt-cached system prompt
│   ├── injector.py             # clipboard save/paste/restore via pywin32; keystroke fallback
│   ├── context.py              # GetForegroundWindow → app name + window title
│   ├── overlay.py              # always-on-top borderless tkinter window; states: recording/processing/error
│   ├── tray.py                 # pystray icon (idle/recording/processing) + right-click menu
│   ├── audio_ducking.py        # Windows Core Audio API: lower other apps' volume during recording
│   └── session.py              # orchestrates one dictation cycle: hotkey down → audio→STT→cleanup→inject
└── tests/
    ├── test_cleanup_prompt.py  # golden tests: raw transcripts in, cleaned text out
    ├── test_injector.py        # clipboard save/restore correctness
    ├── test_session_flow.py    # mocked end-to-end session
    └── fixtures/
        └── transcripts.yaml    # corpus of raw → cleaned pairs by app context
```

**Module boundaries:**

| Module | Public interface | Depends on |
|---|---|---|
| `config.py` | `load() -> Config` | (none — stdlib only) |
| `hotkey.py` | `listen(on_down, on_up)` | pynput |
| `audio.py` | `Recorder.start()`, `Recorder.stop() -> bytes` | sounddevice |
| `stt.py` | `async def stream(audio_iter, keyterms) -> AsyncIterator[Transcript]` | websockets, base64 |
| `cleanup.py` | `async def polish(text, app_context) -> str` | anthropic |
| `injector.py` | `paste(text)` | pywin32 |
| `context.py` | `current_app() -> AppContext` | pywin32 |
| `overlay.py` | `Overlay.show()`, `set_state(state, text)`, `dismiss()` | tkinter |
| `tray.py` | `Tray.run(menu_items)` | pystray, Pillow |
| `audio_ducking.py` | `duck(percent)`, `restore()` | pycaw |
| `session.py` | `async def run_session()` | all of the above |

**Threading model:** async core, sync edges. `stt.py` and `cleanup.py` are async (network I/O). `hotkey.py`, `audio.py`, `injector.py`, `tray.py`, `overlay.py` run on their own threads and post events to the async loop via `asyncio.Queue` and `asyncio.run_coroutine_threadsafe`. Tkinter and pystray each demand their own thread, which the design accepts.

## 5. The cleanup prompt

The single most important piece. Sent every call with prompt caching enabled on the Anthropic API for ~90% input-token discount.

**System prompt:**

```
You are a dictation cleanup assistant. The user spoke into a voice
dictation tool; you receive the raw speech-to-text transcript. Your
job is to return ONLY the cleaned text the user intended to type.

Rules — apply ALL of them:
  1. Remove filler words: um, uh, er, like (when used as filler),
     you know, I mean, sort of (when used as filler).
  2. Add correct punctuation and capitalization. Break into sentences
     and paragraphs where natural.
  3. Resolve self-corrections. If the user said something then
     corrected themselves, keep only the corrected version.
     Examples:
       "meet Tuesday — wait, Wednesday"  →  "meet Wednesday"
       "send to John, no, send to Sarah" →  "send to Sarah"
  4. Fix obvious STT errors using surrounding context (e.g.
     "right" vs "write" vs "rite").
  5. Lightly adapt tone to the active app:
       - Slack / Discord / Teams / iMessage  → casual, no greetings
       - Gmail / Outlook                     → polite, complete sentences
       - VS Code / Cursor / IDE / terminal   → terse, technical, preserve
                                               identifiers verbatim
       - Other / unknown                     → neutral, preserve verbatim
  6. NEVER add information the user did not say.
  7. NEVER reorganize or summarize. Only clean.
  8. If the user gives an explicit formatting instruction inline
     ("...new paragraph...", "...bullet list..."), apply it and
     remove the instruction from the output.
  9. Preserve emojis, proper nouns, and code/identifiers exactly.
 10. Output ONLY the cleaned text. No preface, no quotes, no
     explanation.

Active app: {app_name}
Window title: {window_title}
```

**User message:** the raw Scribe transcript.

**Why this shape:**
- Rules 6 and 7 are the guardrails that stop the LLM from "improving" meaning — the failure mode users complain about most.
- Rule 8 enables power-user voice formatting commands ("new paragraph", "bullet list") without a separate command mode.
- Rule 5 makes the tool feel context-aware without per-app configuration.
- Prompt caching makes each call cost ~$0.0001 input + a tiny output. At 30 min/day, monthly cleanup cost is under $1.

**Golden test corpus** (`tests/fixtures/transcripts.yaml`) — seed with these, grow over time:

| App | Raw | Expected |
|---|---|---|
| Slack | "um yeah I can do the meeting at like uh three actually four works better" | "Yeah, I can do the meeting at four." |
| Gmail | "hi John thanks for the email I'll get back to you um by Friday" | "Hi John, thanks for the email. I'll get back to you by Friday." |
| VS Code | "rename the function get cwd to get current working directory" | "Rename the function `getCwd` to `getCurrentWorkingDirectory`." |
| Cursor | "new paragraph the issue is the websocket reconnects too aggressively" | "The issue is the websocket reconnects too aggressively." (with paragraph break) |

## 6. Latency and error handling

**Latency budget — target end-to-end ≤ 1.2 s from hotkey-up to text appearing:**

| Stage | Budget |
|---|---|
| Final audio chunk → Scribe commit | ~150 ms |
| Cleanup call to Haiku | ~400 ms |
| Clipboard set + Ctrl+V + restore | ~150 ms |
| **Total perceived latency** | **~700 ms** |

**Error matrix — fail-soft, always preserve the user's words:**

| Failure | Behavior |
|---|---|
| ElevenLabs WebSocket fails to connect | Tray icon turns red, toast notification, overlay shows "STT unavailable", session aborts. No injection. |
| Connection drops mid-recording | Send buffered audio to Scribe batch endpoint as fallback; if that fails, dump raw audio to `%TEMP%\voice-operator\unsent\` and notify. |
| Scribe returns empty / VAD-only | Silently dismiss overlay, no injection. |
| Anthropic call fails or exceeds 1500 ms | Inject **raw Scribe transcript**, tray icon flashes orange briefly. |
| Clipboard injection fails (target app rejects paste) | Fall back to keystroke synthesis. Log the app name to build a per-app denylist over time. |
| Right Alt held >60 s | Auto-stop, treat as hotkey-up. Prevents runaway recording. |
| Mic in use by another app | Toast: "Mic unavailable", no recording starts. |

## 7. Small details that matter

- **Audio ducking** — lower other apps' audio by ~70% via Windows Core Audio (pycaw). Restore on stop. This is what makes dictation work in a noisy room.
- **Self-mute detection** — if Teams/Zoom/Discord has the mic, surface a clear error and don't duck (they manage their own audio).
- **Clipboard race-condition guard** — restore original clipboard on a 150 ms delay; extend to 500 ms for apps with known delayed-paste behavior (tracked per-app).
- **Overlay positioning** — always-on-top, borderless, ~280×60 px, anchored bottom-center of the active monitor. Live partials in faded gray; final transcript in white during cleanup spinner; then dismisses.
- **Logging** — rotating logs at `%APPDATA%\voice-operator\logs\`. Each session logs: timestamp, app name, raw transcript, cleaned transcript, per-stage latency. **No audio is logged.** Useful for tuning the prompt.
- **Config file** — `%APPDATA%\voice-operator\config.yaml`:
  ```yaml
  elevenlabs_api_key: sk_...
  anthropic_api_key: sk-ant-...
  hotkey: right_alt            # override available
  hold_or_toggle: hold
  scribe_keyterms:              # up to 100 domain-specific terms
    - "Claude Code"
    - "Anthropic"
    - "Yash"
  cleanup_system_prompt_override: null   # leave null to use bundled prompt
  max_recording_seconds: 60
  ```
- **No telemetry, no auto-update, no auth.** Personal tool. User owns the keys, owns the logs.

## 8. Cost estimate (personal use)

| Component | Assumed usage | Monthly cost |
|---|---|---|
| Scribe v2 Realtime | 30 min/day = 15 hr/mo | Included in existing ElevenLabs Pro (254 hrs/mo included) — **$0 marginal** |
| Claude Haiku 4.5 cleanup | ~30 calls/day × 30 days, ~150 input tokens (cached) + ~80 output tokens per call | **~$0.50–$1/mo** |
| **Total marginal cost** | | **~$1/month** |

## 9. Out of scope for v1

Explicitly deferred to keep this shippable:

- **Command Mode** (select text → speak edit instruction). Future v2 feature; would reuse the same cleanup pipeline with a different system prompt and a separate hotkey.
- **Personal dictionary auto-learning.** v1 uses manually edited `scribe_keyterms` in config. Auto-learning from corrections requires tracking edit deltas, which adds significant complexity.
- **Settings GUI.** Edit the YAML.
- **Cross-platform.** Windows only. macOS and Linux are possible later but the injection layer is OS-specific.
- **Multi-language switching.** English only at start. Scribe supports 90+; would just need a config flag and a re-tested cleanup prompt.
- **VAD-based auto-stop.** Hotkey-release is sufficient and more predictable.
- **Telemetry and auto-update.** Personal tool, manual updates.

## 10. Open questions for the implementation phase

- **uv vs poetry vs pip+venv?** Recommend `uv` for speed; defer to implementation plan.
- **Test runner: pytest vs unittest?** Recommend pytest with pytest-asyncio.
- **Icon assets** — need three tray icon states (idle/recording/processing) and an app icon. Can ship with simple bundled PNGs and replace later.
- **Pre-built executable?** Consider PyInstaller in a follow-up; v1 runs via `python -m voice_operator` from a venv.
