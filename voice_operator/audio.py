from __future__ import annotations

import logging
import queue
from typing import Iterator

import sounddevice as sd

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
CHUNK_MS = 100
BYTES_PER_CHUNK = int(SAMPLE_RATE * (CHUNK_MS / 1000)) * 2  # int16 = 2 bytes/sample


def chunk_bytes(data: bytes, size: int = BYTES_PER_CHUNK) -> Iterator[bytes]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


class Recorder:
    """Capture mic audio into a thread-safe queue of PCM byte chunks."""

    def __init__(self):
        self._q: queue.Queue[bytes] = queue.Queue()
        self._stream: sd.RawInputStream | None = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            log.debug("audio status: %s", status)
        self._q.put(bytes(indata))

    def start(self) -> None:
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=int(SAMPLE_RATE * (CHUNK_MS / 1000)),
            callback=self._callback,
        )
        self._stream.start()

    def drain(self) -> bytes:
        """Pop all currently-queued audio (non-blocking)."""
        out = bytearray()
        while not self._q.empty():
            out += self._q.get_nowait()
        return bytes(out)

    def stop(self) -> bytes:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        return self.drain()
