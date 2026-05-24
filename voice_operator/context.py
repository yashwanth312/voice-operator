from __future__ import annotations

from dataclasses import dataclass

import win32gui
import win32process

try:
    import psutil  # optional; we fall back if absent
except ImportError:  # pragma: no cover
    psutil = None

_FRIENDLY = {
    "slack.exe": "Slack",
    "discord.exe": "Discord",
    "teams.exe": "Teams",
    "ms-teams.exe": "Teams",
    "code.exe": "VS Code",
    "cursor.exe": "Cursor",
    "outlook.exe": "Outlook",
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "firefox.exe": "Firefox",
    "notepad.exe": "Notepad",
    "windowsterminal.exe": "Terminal",
    "powershell.exe": "Terminal",
    "cmd.exe": "Terminal",
}


@dataclass
class AppContext:
    app_name: str
    window_title: str


def friendly_app_name(exe_name: str) -> str:
    if not exe_name:
        return "Unknown"
    key = exe_name.lower()
    if key in _FRIENDLY:
        return _FRIENDLY[key]
    return exe_name[:-4] if key.endswith(".exe") else exe_name


def _exe_for_pid(pid: int) -> str:
    if psutil is not None:
        try:
            return psutil.Process(pid).name()
        except Exception:
            return ""
    try:
        handle = win32process.OpenProcess(0x0400 | 0x0010, False, pid)
        path = win32process.GetModuleFileNameEx(handle, 0)
        return path.rsplit("\\", 1)[-1]
    except Exception:
        return ""


def current_app() -> AppContext:
    """Best-effort foreground app context. Never raises."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe = _exe_for_pid(pid)
        return AppContext(app_name=friendly_app_name(exe), window_title=title[:200])
    except Exception:
        return AppContext(app_name="Unknown", window_title="")
