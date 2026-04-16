"""Medicus Dictate — entry point.

Wires hotkey → recorder → transcriber → injector, with a tray icon reflecting state.
"""
from __future__ import annotations

import sys
import threading
import traceback

from . import config as config_mod
from .hotkey import HotkeyListener
from .injector import Injector
from .recorder import Recorder
from .state import AppState, StateBus
from .transcriber import Transcriber
from .tray import TrayApp


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]

    cfg = config_mod.load()
    print(f"[medicus-dictate] config loaded: model={cfg.model.name} "
          f"device={cfg.model.device} hotkey={cfg.hotkey.combo}")

    bus = StateBus()
    recorder = Recorder(cfg.audio)
    transcriber = Transcriber(cfg.model)
    injector = Injector(cfg.injection)

    # Warm-load the model before accepting hotkey toggles.
    print("[medicus-dictate] loading model (first run may download ~470MB)...")
    transcriber.load()
    print("[medicus-dictate] model ready.")

    def on_toggle() -> None:
        state = bus.current
        if state == AppState.IDLE:
            bus.set(AppState.RECORDING)
            recorder.start()
        elif state == AppState.RECORDING:
            audio = recorder.stop()
            bus.set(AppState.TRANSCRIBING)
            threading.Thread(
                target=_process,
                args=(audio, transcriber, injector, bus),
                daemon=True,
            ).start()
        # TRANSCRIBING / INJECTING: ignore toggle presses while busy.

    listener = HotkeyListener(cfg.hotkey.combo, on_toggle)
    listener.start()

    tray = TrayApp(bus, on_quit=lambda: _shutdown(listener, recorder))
    try:
        tray.run()  # blocks
    finally:
        _shutdown(listener, recorder)

    return 0


def _process(audio, transcriber: Transcriber, injector: Injector, bus: StateBus) -> None:
    try:
        text = transcriber.transcribe(audio)
        if not text.strip():
            bus.last_error = "no speech detected"
            bus.set(AppState.IDLE)
            return
        bus.last_transcript = text
        bus.set(AppState.INJECTING)
        injector.inject(text)
    except Exception as e:
        bus.last_error = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    finally:
        bus.set(AppState.IDLE)


def _shutdown(listener: HotkeyListener, recorder: Recorder) -> None:
    try:
        listener.stop()
    except Exception:
        pass
    try:
        recorder.abort()
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
