from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from functools import partial
from logging.handlers import RotatingFileHandler
from pathlib import Path

import voice_operator.cleanup as _cleanup
from voice_operator import config as cfg_mod
from voice_operator import hotkey, stt
from voice_operator.audio import Recorder
from voice_operator.audio_ducking import AudioDucker
from voice_operator.context import current_app
from voice_operator.injector import paste
from voice_operator.overlay import Overlay
from voice_operator.session import Components, run_dictation_cycle
from voice_operator.tray import Tray

log = logging.getLogger("voice_operator")


def _setup_logging() -> None:
    log_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "voice-operator" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / "voice-operator.log", maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def main() -> None:
    args = sys.argv[1:]
    if "--install-autostart" in args:
        from voice_operator import autostart
        path = autostart.install()
        print(f"Autostart installed - Voice Operator will launch at login.\nShortcut: {path}")
        return
    if "--uninstall-autostart" in args:
        from voice_operator import autostart
        removed = autostart.uninstall()
        print("Autostart removed." if removed else "No autostart shortcut was installed.")
        return

    _setup_logging()
    config = cfg_mod.load_config()

    overlay = Overlay()
    overlay.start()
    quit_event = threading.Event()
    tray = Tray(on_quit=quit_event.set)
    tray.start()

    loop = asyncio.new_event_loop()
    recorder = Recorder()
    ducker = AudioDucker()

    components = Components(
        recorder=recorder,
        ducker=ducker,
        overlay=overlay,
        make_scribe=lambda: stt.ScribeSession(config.elevenlabs_api_key, config.scribe_keyterms),
        polish=partial(_cleanup.polish, api_key=config.groq_api_key),
        inject=paste,
        get_context=current_app,
        set_tray_state=tray.set_state,
        api_key_eleven=config.elevenlabs_api_key,
        cleanup_model=config.cleanup_model,
        prompt_override=config.cleanup_system_prompt_override,
        max_seconds=config.max_recording_seconds,
    )

    state = {"stop_event": None}

    def on_down() -> None:
        stop_event = asyncio.Event()
        state["stop_event"] = stop_event
        asyncio.run_coroutine_threadsafe(run_dictation_cycle(components, stop_event), loop)

    def on_up() -> None:
        ev = state.get("stop_event")
        if ev is not None:
            loop.call_soon_threadsafe(ev.set)

    listener = hotkey.listen(on_down, on_up)

    def _run_loop() -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    loop_thread = threading.Thread(target=_run_loop, daemon=True)
    loop_thread.start()

    log.info("Voice Operator running. Hold Right Alt to dictate. Quit from the tray.")
    quit_event.wait()
    listener.stop()
    loop.call_soon_threadsafe(loop.stop)


if __name__ == "__main__":
    main()
