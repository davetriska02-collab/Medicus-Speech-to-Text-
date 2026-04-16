from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Optional, Tuple

import pystray
from PIL import Image, ImageDraw

from .state import AppState, StateBus


# State → (fill colour hex, tooltip text)
_STYLE: Dict[AppState, tuple[str, str]] = {
    AppState.IDLE: ("#808080", "Medicus Dictate — idle"),
    AppState.RECORDING: ("#d62828", "Medicus Dictate — recording"),
    AppState.TRANSCRIBING: ("#f4a261", "Medicus Dictate — transcribing"),
    AppState.INJECTING: ("#2a9d8f", "Medicus Dictate — injecting"),
}

_ICON_SIZE = 64
# RMS value that maps to "fully bright". Typical speech peaks ~0.2, so 0.25 is
# a reasonable top-of-scale.
_RMS_FULL_SCALE = 0.25


def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _make_icon(colour: str, size: int = _ICON_SIZE) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, size - 4, size - 4), fill=colour, outline="#202020", width=2)
    return img


def _make_recording_icon(rms_bucket: int, peak_bucket: int, size: int = _ICON_SIZE) -> Image.Image:
    """Recording icon: red disc whose brightness tracks RMS, with a peak bar at the bottom.

    rms_bucket: 0..9  — dimmer → brighter.
    peak_bucket: 0..9 — bar width from 0 to near-full-width.
    """
    bright = 0.45 + 0.55 * (rms_bucket / 9.0)   # 0.45..1.0
    r, g, b = _hex_to_rgb(_STYLE[AppState.RECORDING][0])
    fill = (int(r * bright), int(g * bright), int(b * bright), 255)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Shrink the disc slightly to leave room for the peak bar.
    d.ellipse((4, 4, size - 4, size - 12), fill=fill, outline="#202020", width=2)

    # Peak bar: grey track + white fill proportional to peak.
    track_y0, track_y1 = size - 8, size - 4
    d.rectangle((4, track_y0, size - 4, track_y1), fill="#303030")
    bar_w = int((size - 8) * (peak_bucket / 9.0))
    if bar_w > 0:
        d.rectangle((4, track_y0, 4 + bar_w, track_y1), fill="#ffffff")
    return img


class TrayApp:
    def __init__(
        self,
        bus: StateBus,
        on_quit: Callable[[], None],
        hotkey_combo: str = "",
        show_first_run_hint: bool = False,
        level_provider: Optional[Callable[[], Tuple[float, float]]] = None,
        on_read_last: Optional[Callable[[], None]] = None,
        on_scratch_last: Optional[Callable[[], None]] = None,
    ) -> None:
        self.bus = bus
        self.on_quit = on_quit
        self.hotkey_combo = hotkey_combo
        self.show_first_run_hint = show_first_run_hint
        self.level_provider = level_provider
        self.on_read_last = on_read_last
        self.on_scratch_last = on_scratch_last

        self._static_images = {state: _make_icon(colour) for state, (colour, _) in _STYLE.items()}
        self._rec_cache: Dict[Tuple[int, int], Image.Image] = {}
        self._last_state = AppState.IDLE
        self._stop = threading.Event()
        self._painter_thread: Optional[threading.Thread] = None

        # Dynamic "Recent" submenu — built fresh each time the tray menu opens.
        def _recent_items():
            hist = self.bus.get_history()
            if not hist:
                return (pystray.MenuItem("(no dictations yet)", None, enabled=False),)
            items = []
            # Most-recent first.
            for entry in reversed(hist):
                preview = entry.replace("\n", " / ")
                if len(preview) > 60:
                    preview = preview[:57] + "..."
                items.append(pystray.MenuItem(
                    preview,
                    # Default binding capture for `entry`.
                    lambda icon, item, t=entry: self._copy_history_entry(t),
                ))
            return tuple(items)

        hotkey_label = f"Hotkey: {hotkey_combo}" if hotkey_combo else "Hotkey: (unset)"

        self._icon = pystray.Icon(
            "medicus-dictate",
            icon=self._static_images[AppState.IDLE],
            title=_STYLE[AppState.IDLE][1],
            menu=pystray.Menu(
                pystray.MenuItem(hotkey_label, None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Show last transcription", self._show_last),
                pystray.MenuItem("Read last aloud", self._read_last,
                                 enabled=bool(self.on_read_last)),
                pystray.MenuItem("Scratch last (backspace it)", self._scratch_last,
                                 enabled=bool(self.on_scratch_last)),
                pystray.MenuItem("Recent", pystray.Menu(_recent_items)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Show last error", self._show_last_error),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._quit),
            ),
        )
        bus.subscribe(self._on_state)
        bus.set_toast_handler(self._toast)

    # ------------------------------------------------------------------ events
    def _on_state(self, state: AppState) -> None:
        tooltip = _STYLE[state][1]
        self._icon.title = tooltip
        if state != AppState.RECORDING:
            self._icon.icon = self._static_images[state]
        # Surface any error raised during this pipeline run (transcribe OR
        # inject). `last_error` is reset at the start of every _process call,
        # so a stale error from a previous run won't re-toast.
        if state == AppState.IDLE and self._last_state != AppState.IDLE:
            err = self.bus.last_error
            if err:
                self._toast("Medicus Dictate — error", err)
        self._last_state = state

    def _toast(self, title: str, body: str) -> None:
        try:
            self._icon.notify(body[:256], title)
        except Exception:
            pass

    # ----------------------------------------------------------------- actions
    def _show_last(self, icon, item) -> None:
        text = self.bus.last_transcript or "(no transcription yet)"
        icon.notify(text[:256], "Last transcription")

    def _show_last_error(self, icon, item) -> None:
        err = self.bus.last_error or "(no errors)"
        icon.notify(err[:256], "Last error")

    def _read_last(self, icon, item) -> None:
        if self.on_read_last is not None:
            try:
                self.on_read_last()
            except Exception as e:
                icon.notify(str(e)[:256], "Read failed")

    def _scratch_last(self, icon, item) -> None:
        if self.on_scratch_last is not None:
            try:
                self.on_scratch_last()
            except Exception as e:
                icon.notify(str(e)[:256], "Scratch failed")

    def _copy_history_entry(self, text: str) -> None:
        # Put the selected history entry onto the clipboard so the clinician
        # can paste it wherever they want. Doesn't auto-inject because that
        # could go to the wrong field.
        try:
            import pyperclip
            pyperclip.copy(text)
            self._icon.notify(text[:120], "Copied to clipboard")
        except Exception as e:
            self._icon.notify(str(e)[:256], "Copy failed")

    def _quit(self, icon, item) -> None:
        self._stop.set()
        try:
            self.on_quit()
        finally:
            icon.stop()

    # ---------------------------------------------------------------- painter
    def _rec_icon(self, rms: float, peak: float) -> Image.Image:
        rms_b = max(0, min(9, int((rms / _RMS_FULL_SCALE) * 9)))
        peak_b = max(0, min(9, int(peak * 9)))
        key = (rms_b, peak_b)
        cached = self._rec_cache.get(key)
        if cached is None:
            cached = _make_recording_icon(rms_b, peak_b)
            self._rec_cache[key] = cached
        return cached

    def _painter_loop(self) -> None:
        last_key: Optional[Tuple[int, int]] = None
        while not self._stop.is_set():
            if self._last_state == AppState.RECORDING and self.level_provider is not None:
                rms, peak = self.level_provider()
                rms_b = max(0, min(9, int((rms / _RMS_FULL_SCALE) * 9)))
                peak_b = max(0, min(9, int(peak * 9)))
                key = (rms_b, peak_b)
                if key != last_key:
                    self._icon.icon = self._rec_icon(rms, peak)
                    last_key = key
            else:
                last_key = None
            time.sleep(1.0 / 15.0)

    # ------------------------------------------------------------------- boot
    def _setup(self, icon: pystray.Icon) -> None:
        icon.visible = True
        self._painter_thread = threading.Thread(target=self._painter_loop, daemon=True)
        self._painter_thread.start()
        if self.show_first_run_hint:
            hint = (
                f"Press {self.hotkey_combo} to start recording, "
                "press again to stop. Transcription is pasted at the cursor. "
                "Check Windows mic permissions if recording fails."
            )
            self._toast("Medicus Dictate ready", hint)

    def run(self) -> None:
        self._icon.run(setup=self._setup)
