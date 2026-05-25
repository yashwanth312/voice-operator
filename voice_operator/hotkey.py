from __future__ import annotations

import logging
from typing import Callable

from pynput import keyboard

log = logging.getLogger(__name__)


class HotkeyState:
    """Debounces key auto-repeat so on_down/on_up each fire exactly once per hold."""

    def __init__(self, on_down: Callable[[], None], on_up: Callable[[], None]):
        self._on_down = on_down
        self._on_up = on_up
        self._held = False

    def key_pressed(self) -> None:
        if self._held:
            return
        self._held = True
        self._on_down()

    def key_released(self) -> None:
        if not self._held:
            return
        self._held = False
        self._on_up()


# The physical Right Alt key reports as alt_r on US layouts and as alt_gr
# (AltGr) on many international layouts; both are virtual-key 165 (VK_RMENU).
# Accept either so "Right Alt" works regardless of layout.
_RIGHT_ALT_KEYS = frozenset({keyboard.Key.alt_r, keyboard.Key.alt_gr})


def is_right_alt(key) -> bool:
    return key in _RIGHT_ALT_KEYS


def listen(on_down: Callable[[], None], on_up: Callable[[], None]) -> keyboard.Listener:
    """Start a global listener for Right Alt press-and-hold. Returns the running listener."""
    state = HotkeyState(on_down, on_up)

    def _on_press(key):
        if is_right_alt(key):
            log.info("Right Alt pressed — starting dictation")
            state.key_pressed()

    def _on_release(key):
        if is_right_alt(key):
            log.info("Right Alt released — stopping dictation")
            state.key_released()

    listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
    listener.start()
    log.info("Hotkey listener started successfully")
    return listener
