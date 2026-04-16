"""Local text-to-speech via pyttsx3 (SAPI on Windows).

Used for the "Read last" tray action and the "read that back" voice command.
No network. Speak happens on a worker thread so the main/tray thread
doesn't block on SAPI.
"""
from __future__ import annotations

import threading
from typing import Optional

from .config import TTSConfig


class TTSEngine:
    def __init__(self, cfg: TTSConfig) -> None:
        self.cfg = cfg
        self._engine = None
        self._lock = threading.Lock()

    def _ensure_engine(self):
        # Lazy: don't pay the SAPI init cost unless the user actually uses TTS.
        if self._engine is not None:
            return self._engine
        try:
            import pyttsx3
        except ImportError:
            return None
        try:
            eng = pyttsx3.init()
        except Exception as e:
            print(f"[tts] init failed: {e}")
            return None
        try:
            eng.setProperty("rate", int(self.cfg.rate))
        except Exception:
            pass
        if self.cfg.voice:
            try:
                eng.setProperty("voice", self.cfg.voice)
            except Exception:
                pass
        self._engine = eng
        return eng

    def speak(self, text: str) -> None:
        if not self.cfg.enabled or not text:
            return

        def _run() -> None:
            with self._lock:
                eng = self._ensure_engine()
                if eng is None:
                    print("[tts] engine unavailable, skipping read")
                    return
                try:
                    eng.say(text)
                    eng.runAndWait()
                except Exception as e:
                    print(f"[tts] say failed: {e}")

        threading.Thread(target=_run, daemon=True).start()
