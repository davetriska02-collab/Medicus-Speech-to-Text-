"""Medicus Dictate — entry point.

Wires hotkey → recorder → transcriber → injector, with a tray icon reflecting state.
"""
from __future__ import annotations

import sys
import threading
import time
import traceback

from . import config as config_mod
from . import postprocess
from . import smart
from . import voice_commands
from .hotkey import HotkeyListener
from .injector import Injector
from .recorder import Recorder
from .state import AppState, StateBus
from .transcriber import Transcriber
from .tray import TrayApp


def main(argv: list[str] | None = None) -> int:
    try:
        cfg = config_mod.load()
    except FileNotFoundError:
        print(
            f"[medicus-dictate] config.toml not found at {config_mod.DEFAULT_CONFIG_PATH}.\n"
            "Copy the shipped config.toml next to the exe (or into the project root "
            "for dev runs) and try again.",
            file=sys.stderr,
        )
        return 2
    except Exception as e:
        print(f"[medicus-dictate] failed to load config: {e}", file=sys.stderr)
        return 2
    print(f"[medicus-dictate] config loaded: model={cfg.model.name} "
          f"device={cfg.model.device} hotkey={cfg.hotkey.combo}")

    bus = StateBus()
    recorder = Recorder(cfg.audio)
    transcriber = Transcriber(cfg.model)
    injector = Injector(cfg.injection)
    first_run = _is_first_run()
    # Serialises on_toggle so a fast double-press can't race around the
    # state-check -> stream-open -> state-flip sequence.
    toggle_lock = threading.Lock()

    # Warm-load the model before accepting hotkey toggles.
    print("[medicus-dictate] loading model (first run may download ~470MB)...")
    transcriber.load()
    print("[medicus-dictate] model ready.")

    def on_toggle() -> None:
        with toggle_lock:
            state = bus.current
            if state == AppState.IDLE:
                # Open the stream BEFORE flipping state, so a failure (bad device,
                # mic already held) doesn't leave us stuck in RECORDING.
                try:
                    recorder.start()
                except Exception as e:
                    msg = f"{type(e).__name__}: {e}"
                    bus.last_error = f"audio start failed: {msg}"
                    bus.toast("Medicus Dictate — mic error", msg)
                    return
                bus.set(AppState.RECORDING)
                threading.Thread(
                    target=_silence_watchdog,
                    args=(recorder, bus),
                    daemon=True,
                ).start()
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
    try:
        listener.start()
    except Exception as e:
        print(
            f"[medicus-dictate] failed to register global hotkey {cfg.hotkey.combo!r}: {e}\n"
            "Another application may already own this key combination. Edit "
            "config.toml and restart.",
            file=sys.stderr,
        )
        return 3

    tray = TrayApp(
        bus,
        on_quit=lambda: _shutdown(listener, recorder),
        hotkey_combo=cfg.hotkey.combo,
        show_first_run_hint=first_run,
        level_provider=recorder.current_level,
    )
    try:
        tray.run()  # blocks
    finally:
        _shutdown(listener, recorder)
        if first_run:
            _mark_first_run_done()

    return 0


def _process(audio, transcriber, injector, bus, cfg) -> None:
    # Clear any stale error from a previous run so the menu / toast logic only
    # surfaces problems from this invocation.
    bus.last_error = ""
    try:
        text = transcriber.transcribe(audio)
        if cfg.commands.enabled:
            text = voice_commands.apply(text)
        text = postprocess.process(text, cfg.postprocess)
        text = smart.tidy(text, cfg.smart)
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


# RMS threshold below which 2s of audio is considered silence. Typical room
# noise is ~0.001–0.003; normal speech RMS sits around 0.03–0.1.
_SILENCE_RMS_THRESHOLD = 0.005
# 3s of grace so a clinician pausing to think before speaking doesn't trip
# the warning.
_SILENCE_TIMEOUT_S = 3.0


def _silence_watchdog(recorder, bus) -> None:
    """Warn once if no audible input is seen within 2s of recording start."""
    t0 = time.monotonic()
    while bus.current == AppState.RECORDING:
        if recorder.max_rms_since_start >= _SILENCE_RMS_THRESHOLD:
            return
        if time.monotonic() - t0 >= _SILENCE_TIMEOUT_S:
            bus.toast(
                "Medicus Dictate — no input",
                "No sound detected. Check your mic is unmuted and selected as "
                "the default recording device.",
            )
            return
        time.sleep(0.2)


if __name__ == "__main__":
    raise SystemExit(main())
