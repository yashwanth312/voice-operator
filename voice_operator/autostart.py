from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Voice Operator"
_SHORTCUT_NAME = "Voice Operator.lnk"


def startup_dir() -> Path:
    """The per-user Startup folder; anything here launches at login (no admin)."""
    return (
        Path(os.environ["APPDATA"])
        / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    )


def shortcut_path() -> Path:
    return startup_dir() / _SHORTCUT_NAME


def windowless_python() -> Path:
    """The venv's pythonw.exe (runs with no console window); fall back to python.exe."""
    pyw = Path(sys.executable).with_name("pythonw.exe")
    return pyw if pyw.exists() else Path(sys.executable)


def install() -> Path:
    """Create a Startup-folder shortcut that launches the daemon at login."""
    import win32com.client  # provided by pywin32

    path = shortcut_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(path))
    shortcut.TargetPath = str(windowless_python())
    shortcut.Arguments = "-m voice_operator"
    shortcut.WorkingDirectory = str(Path(__file__).resolve().parent.parent)
    shortcut.Description = "Voice Operator dictation daemon (launches at login)"
    shortcut.Save()
    return path


def uninstall() -> bool:
    """Remove the Startup shortcut. Returns True if one was present."""
    path = shortcut_path()
    if path.exists():
        path.unlink()
        return True
    return False
