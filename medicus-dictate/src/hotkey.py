from __future__ import annotations

from typing import Callable, Optional

from pynput import keyboard


class HotkeyListener:
    """Wraps pynput.keyboard.GlobalHotKeys with a single toggle callback."""

    def __init__(self, combo: str, on_toggle: Callable[[], None]) -> None:
        self.combo = combo
        self.on_toggle = on_toggle
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = keyboard.GlobalHotKeys({self.combo: self._fire})
        self._listener.start()

    def _fire(self) -> None:
        try:
            self.on_toggle()
        except Exception as e:
            print(f"[hotkey] toggle handler failed: {e}")

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
