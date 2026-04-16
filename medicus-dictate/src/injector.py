from __future__ import annotations

import time

import pyautogui
import pyperclip
from pynput.keyboard import Controller as _KbController, Key as _Key

from .config import InjectionConfig

# Disable pyautogui's fail-safe: if the cursor happens to sit in a screen
# corner when we paste, the default behaviour is to raise FailSafeException
# and drop the transcription. For a dictation tool the user can't predict
# where their cursor is, so this check does more harm than good.
pyautogui.FAILSAFE = False

# Reused Controller; pynput.type() handles Unicode on Windows via SendInput
# with VK_PACKET, which pyautogui.typewrite silently drops.
_keyboard = _KbController()


class Injector:
    """Injects text into the focused field via clipboard paste or character typing.

    Tracks the length of the last injection so `scratch()` can delete it by
    issuing the right number of backspaces. Note: this is only reliable if
    the user hasn't typed or moved the cursor since the last injection.
    """

    def __init__(self, cfg: InjectionConfig) -> None:
        self.cfg = cfg
        self.last_injected_text: str = ""

    def inject(self, text: str) -> None:
        if not text:
            return
        if self.cfg.pre_delay_ms > 0:
            time.sleep(self.cfg.pre_delay_ms / 1000.0)
        if self.cfg.mode == "paste":
            self._paste(text)
        else:
            self._type(text)
        self.last_injected_text = text

    def scratch(self) -> int:
        """Delete the last injection by backspacing. Returns characters removed."""
        text = self.last_injected_text
        if not text:
            return 0
        # Backspace one event per character. Small delay avoids dropped events
        # in fields with slow key handling.
        for _ in range(len(text)):
            _keyboard.press(_Key.backspace)
            _keyboard.release(_Key.backspace)
            time.sleep(0.003)
        removed = len(text)
        self.last_injected_text = ""
        return removed

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
        # pynput emits each character as a SendInput event, including non-ASCII
        # (accented letters, curly quotes, en/em dashes).
        _keyboard.type(text)
