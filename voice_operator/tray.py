from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from voice_operator.config import default_config_path

_COLORS = {"idle": "#4a4a4a", "recording": "#e04545", "processing": "#e0a545"}


_BAR_HEIGHTS = [24, 40, 28]  # left, center, right — classic EQ silhouette
_BAR_W = 12
_BAR_GAP = 5
_BAR_BOTTOM = 52


def _icon_image(state: str) -> Image.Image:
    img = Image.new("RGB", (64, 64), "#1e1e1e")
    d = ImageDraw.Draw(img)
    color = _COLORS.get(state, _COLORS["idle"])
    total_w = len(_BAR_HEIGHTS) * _BAR_W + (len(_BAR_HEIGHTS) - 1) * _BAR_GAP
    x0 = (64 - total_w) // 2
    for i, h in enumerate(_BAR_HEIGHTS):
        bx = x0 + i * (_BAR_W + _BAR_GAP)
        d.rounded_rectangle([bx, _BAR_BOTTOM - h, bx + _BAR_W, _BAR_BOTTOM], radius=3, fill=color)
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
