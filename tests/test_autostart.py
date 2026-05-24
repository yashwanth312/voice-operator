from pathlib import Path

from voice_operator import autostart


def test_shortcut_is_named_lnk_in_startup_folder():
    p = autostart.shortcut_path()
    assert p.name == "Voice Operator.lnk"
    assert p.parent == autostart.startup_dir()
    assert "Startup" in str(p)


def test_windowless_python_is_a_python_exe():
    p = autostart.windowless_python()
    assert isinstance(p, Path)
    assert p.name in ("pythonw.exe", "python.exe")
