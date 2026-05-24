from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from voice_operator.config import default_config_path

_COLORS = {"idle": "#4a4a4a", "recording": "#e04545", "processing": "#e0a545"}


def _icon_image(state: str) -> Image.Image:
    img = Image.new("RGB", (64, 64), "#1e1e1e")
    d = ImageDraw.Draw(img)
    d.ellipse((16, 16, 48, 48), fill=_COLORS.get(state, _COLORS["idle"]))
    return img


def _open_log_folder() -> None:
    log_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "voice-operator" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    os.startfile(str(log_dir))  # noqa: S606 - intentional, Windows-only


def _open_config() -> None:
    subprocess.Popen(["notepad.exe", str(default_config_path())])


class Tray:
    """System-tray icon with status state and a menu. Runs on its own thread."""

    def __init__(self, on_quit):
        self._on_quit = on_quit
        self._icon = pystray.Icon(
            "voice-operator",
            icon=_icon_image("idle"),
            title="Voice Operator (idle)",
            menu=pystray.Menu(
                pystray.MenuItem("Open config", lambda: _open_config()),
                pystray.MenuItem("Open log folder", lambda: _open_log_folder()),
                pystray.MenuItem("Quit", self._quit),
            ),
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def set_state(self, state: str) -> None:
        self._icon.icon = _icon_image(state)
        self._icon.title = f"Voice Operator ({state})"

    def _quit(self) -> None:
        self._icon.stop()
        self._on_quit()
