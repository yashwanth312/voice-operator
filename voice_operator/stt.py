from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass

import websockets

log = logging.getLogger(__name__)

WS_URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime"
SAMPLE_RATE = 16000


@dataclass(frozen=True)
class Transcript:
    text: str
    is_final: bool


def parse_message(raw: str) -> Transcript | None:
    # Scribe v2 Realtime tags messages with "message_type" (confirmed against the
    # live API). Transcript text is in "text".
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    mtype = data.get("message_type")
    if mtype == "partial_transcript":
        return Transcript(text=data.get("text", ""), is_final=False)
    if mtype in ("committed_transcript", "committed_transcript_with_timestamps"):
        return Transcript(text=data.get("text", ""), is_final=True)
    return None


def _audio_chunk_message(pcm_bytes: bytes) -> str:
    return json.dumps(
        {
            "message_type": "input_audio_chunk",
            "audio_base_64": base64.b64encode(pcm_bytes).decode("ascii"),
            "sample_rate": SAMPLE_RATE,
        }
    )


def _commit_message() -> str:
    # Finalize by sending an empty audio chunk with the commit flag set (manual
    # commit strategy). There is no separate "commit" message type.
    return json.dumps(
        {"message_type": "input_audio_chunk", "audio_base_64": "", "commit": True}
    )


class ScribeSession:
    """One streaming transcription session. Send audio chunks, then commit() to finalize."""

    def __init__(self, api_key: str, keyterms: list[str]):
        self._api_key = api_key
        # NOTE: keyterm biasing is not wired in v1. The live API rejects a
        # client "session_config" message, and the correct mechanism for keyterms
        # on the realtime socket is not yet confirmed. Kept for forward-compat;
        # config.scribe_keyterms is currently a no-op. TODO: wire via the documented
        # mechanism (likely a query param) once confirmed.
        self._keyterms = keyterms
        self._ws = None

    async def __aenter__(self) -> "ScribeSession":
        # The session starts with sensible defaults (16 kHz PCM, manual commit).
        # Do NOT send a session_config message — the server rejects it.
        self._ws = await websockets.connect(
            WS_URL, additional_headers={"xi-api-key": self._api_key}
        )
        return self

    async def __aexit__(self, *exc):
        if self._ws is not None:
            await self._ws.close()

    async def send_audio(self, pcm_bytes: bytes) -> None:
        await self._ws.send(_audio_chunk_message(pcm_bytes))

    async def commit(self) -> None:
        """Signal end-of-audio so the server emits the committed transcript."""
        await self._ws.send(_commit_message())

    async def consume(self, on_partial) -> str:
        """SINGLE reader for this socket. Dispatches partial transcripts to on_partial
        and returns the committed transcript text once it arrives.

        Exactly one coroutine may read a websocket at a time (websockets forbids
        concurrent recv), so this is the only place we read. Sending audio and the
        commit happen concurrently on the same socket, which is allowed."""
        final_text = ""
        try:
            async for raw in self._ws:
                t = parse_message(raw)
                if t is None:
                    continue
                if t.is_final:
                    return t.text
                on_partial(t.text)
        except (asyncio.CancelledError, websockets.ConnectionClosed):
            pass
        return final_text
