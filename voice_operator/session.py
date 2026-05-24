from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from voice_operator.context import AppContext

log = logging.getLogger(__name__)


@dataclass
class Components:
    recorder: object                       # .start(), .drain()->bytes, .stop()->bytes
    ducker: object                         # .duck(), .restore()
    overlay: object                        # .show/.set_partial/.set_processing/.set_error/.dismiss
    make_scribe: Callable[[], object]      # context-manager: send_audio/listen_partials/commit_and_collect
    polish: Callable[..., Awaitable[str]]  # (text, ctx, *, model, override) -> str
    inject: Callable[[str], None]
    get_context: Callable[[], AppContext]
    set_tray_state: Callable[[str], None]
    api_key_eleven: str
    cleanup_model: str
    prompt_override: str | None
    max_seconds: int


async def run_dictation_cycle(c: Components, stop_event: asyncio.Event) -> None:
    """One full hold-to-talk cycle. stop_event is set when the hotkey is released."""
    ctx = c.get_context()
    c.set_tray_state("recording")
    c.overlay.show("Listening...")
    c.ducker.duck()
    c.recorder.start()

    scribe_cm = c.make_scribe()
    try:
        async with scribe_cm as scribe:
            # ONE reader coroutine for the socket (consume); audio is sent
            # concurrently. Two concurrent recv loops are illegal in websockets.
            reader = asyncio.create_task(scribe.consume(c.overlay.set_partial))
            await _pump_audio(c.recorder, scribe, stop_event, c.max_seconds)
            c.overlay.set_processing("Polishing...")
            await scribe.commit()
            try:
                raw = await asyncio.wait_for(reader, timeout=15.0)
            except asyncio.TimeoutError:
                log.warning("timed out waiting for committed transcript")
                reader.cancel()
                raw = ""
    except Exception:
        log.exception("STT session failed")
        c.overlay.set_error("STT unavailable")
        await asyncio.sleep(1.2)
        _teardown(c)
        return

    if not raw.strip():
        _teardown(c)
        return

    cleaned = await c.polish(
        raw, ctx, model=c.cleanup_model, override=c.prompt_override
    )
    if cleaned.strip():
        c.inject(cleaned)
    _teardown(c)


async def _pump_audio(recorder, scribe, stop_event: asyncio.Event, max_seconds: int) -> None:
    elapsed = 0.0
    while not stop_event.is_set() and elapsed < max_seconds:
        data = recorder.drain()
        if data:
            await scribe.send_audio(data)
        await asyncio.sleep(0.05)
        elapsed += 0.05
    # flush the tail
    tail = recorder.stop()
    if tail:
        await scribe.send_audio(tail)


def _teardown(c: Components) -> None:
    c.recorder.stop()
    c.ducker.restore()
    c.overlay.dismiss()
    c.set_tray_state("idle")
