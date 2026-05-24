import pytest
from voice_operator.injector import _get_clipboard_text, _set_clipboard_text


def test_clipboard_round_trip():
    original = _get_clipboard_text()
    try:
        _set_clipboard_text("voice-operator-test-123")
        assert _get_clipboard_text() == "voice-operator-test-123"
    finally:
        _set_clipboard_text(original or "")


def test_set_empty_string_is_safe():
    _set_clipboard_text("")
    assert _get_clipboard_text() == ""
