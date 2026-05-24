from __future__ import annotations

import logging
import time

import win32clipboard
import win32con
from pynput.keyboard import Controller, Key

log = logging.getLogger(__name__)

_RESTORE_DELAY_SECONDS = 0.15
_keyboard = Controller()


def _get_clipboard_text() -> str:
    win32clipboard.OpenClipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        return ""
    finally:
        win32clipboard.CloseClipboard()


def _set_clipboard_text(text: str) -> None:
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


def _send_paste() -> None:
    _keyboard.press(Key.ctrl)
    _keyboard.press("v")
    _keyboard.release("v")
    _keyboard.release(Key.ctrl)


def paste(text: str) -> None:
    """Inject text into the focused field via clipboard paste, restoring the old clipboard."""
    if not text:
        return
    saved = _get_clipboard_text()
    try:
        _set_clipboard_text(text)
        time.sleep(0.02)
        _send_paste()
        time.sleep(_RESTORE_DELAY_SECONDS)
    except Exception:
        log.exception("clipboard paste failed; falling back to keystrokes")
        type_text(text)
    finally:
        try:
            _set_clipboard_text(saved)
        except Exception:
            log.warning("could not restore clipboard")


def type_text(text: str) -> None:
    """Fallback: type the text character-by-character. Slower but works in odd apps."""
    _keyboard.type(text)
