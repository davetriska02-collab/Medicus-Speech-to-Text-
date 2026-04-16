from __future__ import annotations

import threading
from collections import deque
from enum import Enum
from typing import Callable, Deque, List, Optional


class AppState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    INJECTING = "injecting"


class StateBus:
    """Thread-safe current-state holder with subscriber callbacks."""

    def __init__(self, history_size: int = 5) -> None:
        self._state = AppState.IDLE
        self._lock = threading.Lock()
        self._listeners: List[Callable[[AppState], None]] = []
        self._last_transcript: str = ""
        self._last_error: str = ""
        self._toast_handler: Optional[Callable[[str, str], None]] = None
        self._history: Deque[str] = deque(maxlen=history_size)

    @property
    def current(self) -> AppState:
        with self._lock:
            return self._state

    def set(self, new_state: AppState) -> None:
        with self._lock:
            if new_state == self._state:
                return
            self._state = new_state
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(new_state)
            except Exception:
                pass

    def subscribe(self, cb: Callable[[AppState], None]) -> None:
        with self._lock:
            self._listeners.append(cb)

    @property
    def last_transcript(self) -> str:
        with self._lock:
            return self._last_transcript

    @last_transcript.setter
    def last_transcript(self, value: str) -> None:
        with self._lock:
            self._last_transcript = value

    @property
    def last_error(self) -> str:
        with self._lock:
            return self._last_error

    @last_error.setter
    def last_error(self, value: str) -> None:
        with self._lock:
            self._last_error = value

    def set_toast_handler(self, handler: Callable[[str, str], None]) -> None:
        with self._lock:
            self._toast_handler = handler

    def toast(self, title: str, body: str) -> None:
        with self._lock:
            handler = self._toast_handler
        if handler is None:
            return
        try:
            handler(title, body)
        except Exception:
            pass

    def push_history(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            self._history.append(text)

    def get_history(self) -> list[str]:
        with self._lock:
            return list(self._history)
