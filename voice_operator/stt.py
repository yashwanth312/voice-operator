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
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    mtype = data.get("type")
    if mtype == "partial_transcript":
        return Transcript(text=data.get("text", ""), is_final=False)
    if mtype in ("committed_transcript", "committed_transcript_with_timestamps"):
        return Transcript(text=data.get("text", ""), is_final=True)
    return None


def _audio_chunk_message(pcm_bytes: bytes) -> str:
    return json.dumps(
        {
            "type": "input_audio_chunk",
            "audio_chunk": base64.b64encode(pcm_bytes).decode("ascii"),
        }
    )


def _commit_message() -> str:
    return json.dumps({"type": "commit"})


class ScribeSession:
    """One streaming transcription session. Send audio chunks, then commit() to finalize."""

    def __init__(self, api_key: str, keyterms: list[str]):
        self._api_key = api_key
        self._keyterms = keyterms
        self._ws = None

    async def __aenter__(self) -> "ScribeSession":
        self._ws = await websockets.connect(
            WS_URL, additional_headers={"xi-api-key": self._api_key}
        )
        # Configure the session (keyterm biasing, VAD off — we commit manually).
        await self._ws.send(
            json.dumps(
                {
                    "type": "session_config",
                    "keyterms": self._keyterms,
                    "commit_strategy": "manual",
                }
            )
        )
        return self

    async def __aexit__(self, *exc):
        if self._ws is not None:
            await self._ws.close()

    async def send_audio(self, pcm_bytes: bytes) -> None:
        await self._ws.send(_audio_chunk_message(pcm_bytes))

    async def commit_and_collect(self, timeout: float = 5.0) -> str:
        """Tell the server we're done, then drain messages until the final transcript."""
        await self._ws.send(_commit_message())
        final_text = ""
        try:
            async with asyncio.timeout(timeout):
                async for raw in self._ws:
                    t = parse_message(raw)
                    if t and t.is_final:
                        final_text = t.text
                        break
        except asyncio.TimeoutError:
            log.warning("timed out waiting for committed transcript")
        return final_text

    async def listen_partials(self, on_partial) -> None:
        """Pump partial transcripts to a callback until the socket closes or is cancelled."""
        try:
            async for raw in self._ws:
                t = parse_message(raw)
                if t and not t.is_final:
                    on_partial(t.text)
        except (asyncio.CancelledError, websockets.ConnectionClosed):
            pass
