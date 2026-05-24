from __future__ import annotations

import logging

from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

log = logging.getLogger(__name__)

DUCK_LEVEL = 0.3  # 30% volume == ~70% duck

# Don't touch comms apps (they manage their own audio) or our own process.
_SKIP = {"teams.exe", "ms-teams.exe", "zoom.exe", "discord.exe", "python.exe", "pythonw.exe"}


def should_skip_session(exe_name: str) -> bool:
    return exe_name.lower() in _SKIP


class AudioDucker:
    """Lower other apps' volume during recording; restore exactly on stop."""

    def __init__(self):
        self._saved: list[tuple[ISimpleAudioVolume, float]] = []

    def duck(self) -> None:
        self._saved.clear()
        try:
            for session in AudioUtilities.GetAllSessions():
                if session.Process is None:
                    continue
                if should_skip_session(session.Process.name()):
                    continue
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                current = volume.GetMasterVolume()
                self._saved.append((volume, current))
                volume.SetMasterVolume(current * DUCK_LEVEL, None)
        except Exception:
            log.exception("audio ducking failed; continuing without it")

    def restore(self) -> None:
        for volume, level in self._saved:
            try:
                volume.SetMasterVolume(level, None)
            except Exception:
                log.warning("could not restore one session's volume")
        self._saved.clear()
