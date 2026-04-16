from __future__ import annotations

import time

import pyautogui
import pyperclip

from .config import InjectionConfig

# Disable pyautogui's fail-safe: if the cursor happens to sit in a screen
# corner when we paste, the default behaviour is to raise FailSafeException
# and drop the transcription. For a dictation tool the user can't predict
# where their cursor is, so this check does more harm than good.
pyautogui.FAILSAFE = False


class Injector:
    """Injects text into the focused field via clipboard paste or character typing."""

    def __init__(self, cfg: InjectionConfig) -> None:
        self.cfg = cfg

    def inject(self, text: str) -> None:
        if not text:
            return
        if self.cfg.pre_delay_ms > 0:
            time.sleep(self.cfg.pre_delay_ms / 1000.0)
        if self.cfg.mode == "paste":
            self._paste(text)
        else:
            self._type(text)

    def _paste(self, text: str) -> None:
        # Save existing clipboard contents so the user's copy buffer isn't clobbered.
        try:
            saved = pyperclip.paste()
        except Exception:
            saved = None

        try:
            pyperclip.copy(text)
        except pyperclip.PyperclipException as e:
            raise RuntimeError(f"clipboard write failed: {e}") from e

        # Give the OS a moment to register the clipboard change before pasting.
        time.sleep(0.03)
        try:
            pyautogui.hotkey("ctrl", "v")
        finally:
            # Let the paste complete before restoring the clipboard — even on error,
            # we still want to put the user's original clipboard back.
            time.sleep(0.1)
            if saved is not None:
                try:
                    pyperclip.copy(saved)
                except Exception:
                    pass

    def _type(self, text: str) -> None:
        pyautogui.typewrite(text, interval=0.005)
