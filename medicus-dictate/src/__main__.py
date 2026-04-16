"""Medicus Dictate — entry point.

Wires hotkey → recorder → transcriber → injector, with a tray icon reflecting state.
"""
from __future__ import annotations

import sys
import threading
import traceback

from . import config as config_mod
from . import postprocess
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
    first_run = _is_first_run()

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
                args=(audio, transcriber, injector, bus, cfg),
                daemon=True,
            ).start()
        # TRANSCRIBING / INJECTING: ignore toggle presses while busy.

    listener = HotkeyListener(cfg.hotkey.combo, on_toggle)
    listener.start()

    tray = TrayApp(
        bus,
        on_quit=lambda: _shutdown(listener, recorder),
        hotkey_combo=cfg.hotkey.combo,
        show_first_run_hint=first_run,
    )
    try:
        tray.run()  # blocks
    finally:
        _shutdown(listener, recorder)
        if first_run:
            _mark_first_run_done()

    return 0


def _process(audio, transcriber, injector, bus, cfg) -> None:
    try:
        text = transcriber.transcribe(audio)
        text = postprocess.process(text, cfg.postprocess)
        if not text.strip():
            bus.last_error = "no speech detected"
            return
        bus.last_transcript = text
        bus.set(AppState.INJECTING)
        injector.inject(text)
        _beep_ok()
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


def _first_run_marker() -> "Path":
    from pathlib import Path
    base = Path.home() / ".medicus-dictate"
    base.mkdir(parents=True, exist_ok=True)
    return base / "first-run-done"


def _is_first_run() -> bool:
    return not _first_run_marker().exists()


def _mark_first_run_done() -> None:
    try:
        _first_run_marker().touch()
    except Exception:
        pass


def _beep_ok() -> None:
    # Non-fatal on non-Windows (winsound is Windows-only).
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_OK)
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
