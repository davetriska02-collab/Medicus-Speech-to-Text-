from __future__ import annotations

import queue
import threading
from typing import Optional

import numpy as np
import sounddevice as sd

from .config import AudioConfig


class Recorder:
    """Non-blocking mic capture. Start/stop return numpy float32 audio."""

    def __init__(self, cfg: AudioConfig) -> None:
        self.cfg = cfg
        self._stream: Optional[sd.InputStream] = None
        self._chunks: "queue.Queue[np.ndarray]" = queue.Queue()
        self._lock = threading.Lock()
        # Live level state, updated on the audio callback thread. Python
        # float writes are atomic under the GIL so no lock needed for reads.
        self._rms: float = 0.0
        self._peak: float = 0.0
        self._max_rms: float = 0.0

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            # Overruns etc. are logged but not fatal.
            print(f"[recorder] stream status: {status}")
        chunk = indata.copy()
        self._chunks.put(chunk)
        # Update live-level counters. Decayed peak gives a VU-meter feel.
        data = chunk.reshape(-1)
        rms = float(np.sqrt(np.mean(data * data))) if data.size else 0.0
        peak = float(np.max(np.abs(data))) if data.size else 0.0
        self._rms = rms
        self._peak = max(peak, self._peak * 0.85)
        if rms > self._max_rms:
            self._max_rms = rms

    def current_level(self) -> tuple[float, float]:
        """Return (rms, decayed-peak) since the last callback."""
        return self._rms, self._peak

    @property
    def max_rms_since_start(self) -> float:
        return self._max_rms

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            # Drain any stale chunks from a previous session.
            while not self._chunks.empty():
                self._chunks.get_nowait()
            self._rms = 0.0
            self._peak = 0.0
            self._max_rms = 0.0
            self._stream = sd.InputStream(
                samplerate=self.cfg.sample_rate,
                channels=self.cfg.channels,
                dtype="float32",
                device=self.cfg.device,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> np.ndarray:
        with self._lock:
            if self._stream is None:
                return np.zeros(0, dtype=np.float32)
            self._stream.stop()
            self._stream.close()
            self._stream = None

        parts = []
        while not self._chunks.empty():
            parts.append(self._chunks.get_nowait())
        if not parts:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(parts, axis=0)
        # faster-whisper wants mono float32.
        if audio.ndim == 2 and audio.shape[1] > 1:
            audio = audio.mean(axis=1)
        else:
            audio = audio.reshape(-1)
        return audio.astype(np.float32, copy=False)

    def abort(self) -> None:
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.abort()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None


def _selftest() -> None:
    """Record 5 seconds, write out.wav. Run: python -m src.recorder"""
    import wave
    from .config import load

    cfg = load()
    rec = Recorder(cfg.audio)
    print("Recording 5s...")
    rec.start()
    import time
    time.sleep(5)
    audio = rec.stop()
    print(f"Captured {audio.shape[0] / cfg.audio.sample_rate:.2f}s of audio")

    pcm16 = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open("out.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(cfg.audio.sample_rate)
        w.writeframes(pcm16.tobytes())
    print("Wrote out.wav")


if __name__ == "__main__":
    _selftest()
