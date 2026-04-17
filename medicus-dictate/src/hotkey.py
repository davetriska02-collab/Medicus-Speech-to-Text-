"""Global hotkey with tap vs hold discrimination.

A short press-and-release (≤ hold_threshold_ms) is a *tap* and fires
on_tap — used for the toggle-record behaviour.

A press held longer than the threshold is a *hold* — on_hold_start fires
as the threshold elapses, on_hold_end fires when any key of the combo
is released. Used for push-to-talk.

Built on pynput's low-level Listener (not GlobalHotKeys) because the
latter only signals activation, not release.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional, Set

from pynput import keyboard


class TapHoldHotkey:
    def __init__(
        self,
        combo: str,
        on_tap: Callable[[], None],
        on_hold_start: Callable[[], None],
        on_hold_end: Callable[[], None],
        hold_threshold_ms: int = 300,
    ) -> None:
        self.combo = combo
        self.on_tap = on_tap
        self.on_hold_start = on_hold_start
        self.on_hold_end = on_hold_end
        self.hold_threshold_s = hold_threshold_ms / 1000.0
        try:
            self._required: Set = set(keyboard.HotKey.parse(combo))
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"invalid hotkey combo {combo!r}: {e}. "
                f"Use pynput syntax, e.g. '<ctrl>+<alt>+<space>'."
            ) from e
        self._held: Set = set()
        self._state = "idle"  # "idle" | "down" | "hold"
        self._state_lock = threading.Lock()
        self._hold_timer: Optional[threading.Timer] = None
        self._listener: Optional[keyboard.Listener] = None

    # ------------------------------------------------------------------- lifecycle
    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        with self._state_lock:
            if self._hold_timer is not None:
                self._hold_timer.cancel()
                self._hold_timer = None

    # -------------------------------------------------------------------- internals
    def _canon(self, key):
        try:
            assert self._listener is not None
            return self._listener.canonical(key)
        except Exception:
            return key

    def _on_press(self, key) -> None:
        canon = self._canon(key)
        if canon not in self._required:
            return
        with self._state_lock:
            self._held.add(canon)
            if self._held == self._required and self._state == "idle":
                self._state = "down"
                timer = threading.Timer(self.hold_threshold_s, self._on_hold_threshold)
                timer.daemon = True
                self._hold_timer = timer
                timer.start()

    def _on_hold_threshold(self) -> None:
        fire = False
        with self._state_lock:
            # Tap-at-threshold race: the timer may fire microseconds after a
            # release event started processing. If the keys are no longer all
            # held, treat the press as a tap — the release callback (which
            # raced us for the lock) will handle firing on_tap.
            if self._state == "down" and self._held == self._required:
                self._state = "hold"
                fire = True
                self._hold_timer = None
        if fire:
            _safe_call(self.on_hold_start)

    def _on_release(self, key) -> None:
        canon = self._canon(key)
        if canon not in self._required:
            return
        mode = None
        with self._state_lock:
            self._held.discard(canon)
            if self._state == "down":
                # Released before threshold → tap.
                if self._hold_timer is not None:
                    self._hold_timer.cancel()
                    self._hold_timer = None
                mode = "tap"
                self._state = "idle"
            elif self._state == "hold":
                mode = "hold_end"
                self._state = "idle"
            # "idle" with a stray release (e.g. user released a different
            # modifier first): no-op.
        if mode == "tap":
            _safe_call(self.on_tap)
        elif mode == "hold_end":
            _safe_call(self.on_hold_end)


def _safe_call(fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception as e:
        print(f"[hotkey] callback failed: {e}")
