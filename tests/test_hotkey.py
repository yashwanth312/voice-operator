from pynput import keyboard

from voice_operator.hotkey import HotkeyState, is_right_alt


def test_is_right_alt_accepts_alt_r_and_alt_gr():
    # On many Windows layouts the physical Right Alt key reports as alt_gr
    # (AltGr); both share virtual-key 165 and must count as "Right Alt".
    assert is_right_alt(keyboard.Key.alt_r) is True
    assert is_right_alt(keyboard.Key.alt_gr) is True


def test_is_right_alt_rejects_other_keys():
    assert is_right_alt(keyboard.Key.alt_l) is False
    assert is_right_alt(keyboard.Key.space) is False
    assert is_right_alt(keyboard.KeyCode.from_char("a")) is False


def test_press_then_release_fires_once_each():
    events = []
    state = HotkeyState(on_down=lambda: events.append("down"),
                        on_up=lambda: events.append("up"))
    state.key_pressed()
    state.key_pressed()   # auto-repeat — must be ignored
    state.key_released()
    assert events == ["down", "up"]


def test_release_without_press_is_ignored():
    events = []
    state = HotkeyState(on_down=lambda: events.append("down"),
                        on_up=lambda: events.append("up"))
    state.key_released()
    assert events == []
