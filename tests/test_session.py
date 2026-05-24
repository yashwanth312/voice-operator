import asyncio
import pytest
from voice_operator.session import run_dictation_cycle, Components
from voice_operator.context import AppContext


class FakeRecorder:
    def __init__(self): self.started = self.stopped = False
    def start(self): self.started = True
    def drain(self): return b"\x00\x00"
    def stop(self): self.stopped = True; return b"\x00\x00"


class FakeScribe:
    def __init__(self, *a, **k): self.audio_sent = 0
    async def __aenter__(self): return self
    async def __aexit__(self, *e): return False
    async def send_audio(self, b): self.audio_sent += 1
    async def listen_partials(self, cb): cb("raw partial")
    async def commit_and_collect(self, timeout=5.0): return "um hello world"


class FakeDucker:
    def __init__(self): self.ducked = self.restored = False
    def duck(self): self.ducked = True
    def restore(self): self.restored = True


class Recording:
    def __init__(self): self.partials = []; self.processing = self.dismissed = False
    def show(self, *_): pass
    def set_partial(self, t): self.partials.append(t)
    def set_processing(self, *_): self.processing = True
    def set_error(self, *_): pass
    def dismiss(self): self.dismissed = True


async def test_cycle_records_cleans_and_injects(monkeypatch):
    injected = []
    overlay = Recording()
    ducker = FakeDucker()
    recorder = FakeRecorder()

    async def fake_polish(text, ctx, **kw):
        assert text == "um hello world"
        return "Hello world."

    comps = Components(
        recorder=recorder,
        ducker=ducker,
        overlay=overlay,
        make_scribe=lambda: FakeScribe(),
        polish=fake_polish,
        inject=lambda t: injected.append(t),
        get_context=lambda: AppContext("Slack", "general"),
        set_tray_state=lambda s: None,
        api_key_eleven="x",
        cleanup_model="claude-haiku-4-5",
        prompt_override=None,
        max_seconds=60,
    )

    stop_event = asyncio.Event()
    # Simulate the user releasing the key almost immediately.
    asyncio.get_event_loop().call_soon(stop_event.set)
    await run_dictation_cycle(comps, stop_event)

    assert recorder.started and recorder.stopped
    assert ducker.ducked and ducker.restored
    assert injected == ["Hello world."]
    assert overlay.processing and overlay.dismissed


async def test_empty_transcript_injects_nothing():
    injected = []
    overlay = Recording()

    class EmptyScribe(FakeScribe):
        async def commit_and_collect(self, timeout=5.0): return ""

    async def fake_polish(text, ctx, **kw): return ""

    comps = Components(
        recorder=FakeRecorder(), ducker=FakeDucker(), overlay=overlay,
        make_scribe=lambda: EmptyScribe(), polish=fake_polish,
        inject=lambda t: injected.append(t),
        get_context=lambda: AppContext("Slack", ""),
        set_tray_state=lambda s: None,
        api_key_eleven="x", cleanup_model="claude-haiku-4-5",
        prompt_override=None, max_seconds=60,
    )
    stop_event = asyncio.Event(); stop_event.set()
    await run_dictation_cycle(comps, stop_event)
    assert injected == []
