from voice_operator.hotkey import HotkeyState


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
