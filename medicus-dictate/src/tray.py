from __future__ import annotations

from typing import Callable, Dict

import pystray
from PIL import Image, ImageDraw

from .state import AppState, StateBus


# State → (fill colour, tooltip text)
_STYLE: Dict[AppState, tuple[str, str]] = {
    AppState.IDLE: ("#808080", "Medicus Dictate — idle"),
    AppState.RECORDING: ("#d62828", "Medicus Dictate — recording"),
    AppState.TRANSCRIBING: ("#f4a261", "Medicus Dictate — transcribing"),
    AppState.INJECTING: ("#2a9d8f", "Medicus Dictate — injecting"),
}


def _make_icon(colour: str, size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, size - 4, size - 4), fill=colour, outline="#202020", width=2)
    return img


class TrayApp:
    def __init__(self, bus: StateBus, on_quit: Callable[[], None]) -> None:
        self.bus = bus
        self.on_quit = on_quit
        self._images = {state: _make_icon(colour) for state, (colour, _) in _STYLE.items()}
        self._icon = pystray.Icon(
            "medicus-dictate",
            icon=self._images[AppState.IDLE],
            title=_STYLE[AppState.IDLE][1],
            menu=pystray.Menu(
                pystray.MenuItem("Show last transcription", self._show_last),
                pystray.MenuItem("Show last error", self._show_last_error),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._quit),
            ),
        )
        bus.subscribe(self._on_state)

    def _on_state(self, state: AppState) -> None:
        colour, tooltip = _STYLE[state]
        self._icon.icon = self._images[state]
        self._icon.title = tooltip

    def _show_last(self, icon, item) -> None:
        text = self.bus.last_transcript or "(no transcription yet)"
        icon.notify(text[:256], "Last transcription")

    def _show_last_error(self, icon, item) -> None:
        err = self.bus.last_error or "(no errors)"
        icon.notify(err[:256], "Last error")

    def _quit(self, icon, item) -> None:
        try:
            self.on_quit()
        finally:
            icon.stop()

    def run(self) -> None:
        self._icon.run()
