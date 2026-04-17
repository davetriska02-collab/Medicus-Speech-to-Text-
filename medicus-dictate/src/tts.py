"""Local text-to-speech via pyttsx3 (SAPI on Windows).

Used for the "Read last" tray action and the "read that back" voice command.
No network. Speak happens on a worker thread so the main/tray thread doesn't
block on SAPI.

We construct a fresh engine per `speak()` call. Reusing a single pyttsx3
engine across multiple `runAndWait()` invocations is flaky on Windows SAPI
(second call can hang). The init cost is ~100 ms which is acceptable given
that TTS is user-initiated, not hot-path.
"""
from __future__ import annotations

import threading

from .config import TTSConfig


class TTSEngine:
    def __init__(self, cfg: TTSConfig) -> None:
        self.cfg = cfg
        # Serialises concurrent speak() calls so a user clicking Read twice
        # doesn't try to hold two SAPI engines at once.
        self._lock = threading.Lock()

    def speak(self, text: str) -> None:
        if not self.cfg.enabled or not text:
            return

        def _run() -> None:
            with self._lock:
                try:
                    import pyttsx3
                except ImportError:
                    print("[tts] pyttsx3 not installed, skipping read")
                    return
                try:
                    eng = pyttsx3.init()
                except Exception as e:
                    print(f"[tts] init failed: {e}")
                    return
                try:
                    try:
                        eng.setProperty("rate", int(self.cfg.rate))
                    except Exception:
                        pass
                    if self.cfg.voice:
                        try:
                            eng.setProperty("voice", self.cfg.voice)
                        except Exception:
                            pass
                    eng.say(text)
                    eng.runAndWait()
                except Exception as e:
                    print(f"[tts] say failed: {e}")
                finally:
                    try:
                        eng.stop()
                    except Exception:
                        pass

        threading.Thread(target=_run, daemon=True).start()
