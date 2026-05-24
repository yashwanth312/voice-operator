from __future__ import annotations

import queue
import threading
import tkinter as tk

_BG = "#1e1e1e"
_FG_PARTIAL = "#9aa0a6"
_FG_FINAL = "#ffffff"
_FG_ERROR = "#ff5c5c"


class Overlay:
    """Always-on-top borderless status window driven from any thread via a queue."""

    def __init__(self):
        self._cmd: queue.Queue[tuple] = queue.Queue()
        self._root: tk.Tk | None = None
        self._label: tk.Label | None = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.92)
        self._root.configure(bg=_BG)
        self._label = tk.Label(
            self._root, text="", bg=_BG, fg=_FG_PARTIAL,
            font=("Segoe UI", 12), wraplength=420, justify="left",
        )
        self._label.pack(padx=16, pady=10)
        self._root.withdraw()
        self._poll()
        self._root.mainloop()

    def _poll(self) -> None:
        try:
            while True:
                action, payload = self._cmd.get_nowait()
                if action == "show":
                    self._render(payload, _FG_PARTIAL)
                    self._position_and_show()
                elif action == "partial":
                    self._render(payload or "Listening...", _FG_PARTIAL)
                elif action == "processing":
                    self._render(payload or "Polishing...", _FG_FINAL)
                elif action == "error":
                    self._render(payload, _FG_ERROR)
                elif action == "dismiss":
                    self._root.withdraw()
        except queue.Empty:
            pass
        self._root.after(40, self._poll)

    def _render(self, text: str, color: str) -> None:
        self._label.configure(text=text, fg=color)

    def _position_and_show(self) -> None:
        self._root.update_idletasks()
        w = self._root.winfo_width()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = (sw - w) // 2
        y = sh - 160
        self._root.geometry(f"+{x}+{y}")
        self._root.deiconify()

    # Thread-safe public API
    def show(self, text: str = "Listening...") -> None:
        self._cmd.put(("show", text))

    def set_partial(self, text: str) -> None:
        self._cmd.put(("partial", text))

    def set_processing(self, text: str = "Polishing...") -> None:
        self._cmd.put(("processing", text))

    def set_error(self, text: str) -> None:
        self._cmd.put(("error", text))

    def dismiss(self) -> None:
        self._cmd.put(("dismiss", None))
