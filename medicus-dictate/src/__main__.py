"""Medicus Dictate — entry point.

Wires hotkey → recorder → transcriber → injector, with a tray icon reflecting state.
"""
from __future__ import annotations

import re
import sys
import threading
import time
import traceback
from dataclasses import replace
from typing import Optional

from . import app_detect
from . import config as config_mod
from . import postprocess
from . import smart
from . import voice_commands
from .hotkey import TapHoldHotkey
from .injector import Injector
from .recorder import Recorder
from .state import AppState, StateBus
from .transcriber import Transcriber
from .tray import TrayApp
from .tts import TTSEngine


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

    bus = StateBus(history_size=cfg.history.size)
    recorder = Recorder(cfg.audio)
    transcriber = Transcriber(cfg.model)
    injector = Injector(cfg.injection)
    tts_engine = TTSEngine(cfg.tts)
    first_run = _is_first_run()
    # Serialises hotkey callbacks so tap/hold events can't race around the
    # state-check -> stream-open -> state-flip sequence.
    toggle_lock = threading.Lock()

    # Warm-load the model before accepting hotkey toggles.
    print("[medicus-dictate] loading model (first run may download ~470MB)...")
    transcriber.load()
    print("[medicus-dictate] model ready.")

    # ----------------------------------------------------------- hotkey handlers
    def _start_recording() -> bool:
        """Open the audio stream and flip to RECORDING. Returns False on failure."""
        try:
            recorder.start()
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            bus.last_error = f"audio start failed: {msg}"
            bus.toast("Medicus Dictate — mic error", msg)
            return False
        if cfg.audio.start_cue_enabled:
            _beep_start()
        bus.set(AppState.RECORDING)
        threading.Thread(
            target=_silence_watchdog,
            args=(recorder, bus),
            daemon=True,
        ).start()
        return True

    def _stop_recording_and_process() -> None:
        audio = recorder.stop()
        bus.set(AppState.TRANSCRIBING)
        threading.Thread(
            target=_process,
            args=(audio, transcriber, injector, tts_engine, bus, cfg),
            daemon=True,
        ).start()

    def on_tap() -> None:
        """Short press = toggle."""
        with toggle_lock:
            state = bus.current
            if state == AppState.IDLE:
                _start_recording()
            elif state == AppState.RECORDING:
                _stop_recording_and_process()

    def on_hold_start() -> None:
        """Long press = push-to-talk start."""
        with toggle_lock:
            if bus.current == AppState.IDLE:
                _start_recording()

    def on_hold_end() -> None:
        """Push-to-talk release."""
        with toggle_lock:
            if bus.current == AppState.RECORDING:
                _stop_recording_and_process()

    # ----------------------------------------------------------- wire up
    listener = TapHoldHotkey(
        combo=cfg.hotkey.combo,
        on_tap=on_tap,
        on_hold_start=on_hold_start,
        on_hold_end=on_hold_end,
        hold_threshold_ms=cfg.hotkey.hold_threshold_ms,
    )
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

    def _read_last() -> None:
        tts_engine.speak(bus.last_transcript)

    def _scratch_last_manual() -> None:
        removed = injector.scratch()
        if removed == 0:
            bus.toast("Nothing to scratch", "No recent dictation to undo.")
        else:
            bus.toast("Scratched", f"Removed {removed} characters.")

    tray = TrayApp(
        bus,
        on_quit=lambda: _shutdown(listener, recorder),
        hotkey_combo=cfg.hotkey.combo,
        show_first_run_hint=first_run,
        level_provider=recorder.current_level,
        on_read_last=_read_last,
        on_scratch_last=_scratch_last_manual,
    )
    try:
        tray.run()  # blocks
    finally:
        _shutdown(listener, recorder)
        if first_run:
            _mark_first_run_done()

    return 0


# --------------------------------------------------------------- meta commands

_META_PUNCT_RE = re.compile(r"[^\w\s]")


def _extract_meta_command(raw: str) -> Optional[str]:
    """If the entire utterance is a meta-command, return a token name.

    Meta commands invoke an action instead of being typed. Only triggered
    when the utterance is the command alone — so "scratch that discharge
    note" still transcribes normally.
    """
    stripped = _META_PUNCT_RE.sub("", raw).strip().lower()
    if stripped in ("scratch that", "undo that"):
        return "scratch"
    if stripped in ("read that back", "read last", "read that aloud"):
        return "read"
    return None


# --------------------------------------------------------------- per-app profile

def _profile_for(cfg, exe: str) -> dict:
    if not exe:
        return {}
    return cfg.profiles.get(exe, {}) or {}


def _merged_postprocess_cfg(base, profile: dict):
    custom = {**base.custom, **(profile.get("custom", {}) or {})}
    enable_bnf = profile.get("enable_bnf_frequencies", base.enable_bnf_frequencies)
    return replace(base, custom=custom, enable_bnf_frequencies=enable_bnf)


def _profile_vocab(profile: dict) -> list:
    return list(profile.get("vocabulary", []) or [])


# --------------------------------------------------------------- pipeline

def _process(audio, transcriber, injector, tts_engine, bus, cfg) -> None:
    bus.last_error = ""
    try:
        # Per-app profile — pick up overrides for the focused app (if any).
        exe = app_detect.foreground_exe_name()
        profile = _profile_for(cfg, exe)
        extra_vocab = _profile_vocab(profile)

        raw = transcriber.transcribe(audio, extra_prompt_terms=extra_vocab)

        # Meta-command handling before any formatting / injection.
        meta = _extract_meta_command(raw)
        if meta == "scratch":
            removed = injector.scratch()
            if removed:
                bus.toast("Scratched", f"Removed {removed} characters.")
            else:
                bus.toast("Nothing to scratch", "No recent dictation to undo.")
            return
        if meta == "read":
            tts_engine.speak(bus.last_transcript)
            return

        text = raw
        if cfg.commands.enabled:
            text = voice_commands.apply(text)
        pp_cfg = _merged_postprocess_cfg(cfg.postprocess, profile)
        text = postprocess.process(text, pp_cfg)
        text = smart.tidy(text, cfg.smart)

        if not text.strip():
            bus.last_error = "no speech detected"
            return
        bus.last_transcript = text
        bus.push_history(text)
        bus.set(AppState.INJECTING)
        injector.inject(text)
        _beep_ok()
    except Exception as e:
        bus.last_error = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    finally:
        bus.set(AppState.IDLE)


def _shutdown(listener, recorder: Recorder) -> None:
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
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_OK)
    except Exception:
        pass


def _beep_start() -> None:
    """Brief tick when the mic opens — 'I'm listening' confirmation."""
    try:
        import winsound
        winsound.Beep(900, 40)
    except Exception:
        pass


_SILENCE_RMS_THRESHOLD = 0.005
_SILENCE_TIMEOUT_S = 3.0


def _silence_watchdog(recorder, bus) -> None:
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
