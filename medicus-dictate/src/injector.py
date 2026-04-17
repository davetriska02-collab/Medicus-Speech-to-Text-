from __future__ import annotations

import time

import pyautogui
import pyperclip
from pynput.keyboard import Controller as _KbController, Key as _Key

from . import app_detect
from .config import InjectionConfig

# Disable pyautogui's fail-safe: if the cursor happens to sit in a screen
# corner when we paste, the default behaviour is to raise FailSafeException
# and drop the transcription. For a dictation tool the user can't predict
# where their cursor is, so this check does more harm than good.
pyautogui.FAILSAFE = False

# Reused Controller; pynput.type() handles Unicode on Windows via SendInput
# with VK_PACKET, which pyautogui.typewrite silently drops.
_keyboard = _KbController()


# Sentinel returned when scratch() refuses to act because the foreground
# window has changed since the last injection — deleting from the wrong
# window would be destructive.
SCRATCH_WRONG_WINDOW = -1


class Injector:
    """Injects text into the focused field via clipboard paste or character typing.

    Tracks the length of the last injection and the HWND it targeted so
    `scratch()` can safely delete it — only if the same window still has
    focus.
    """

    def __init__(self, cfg: InjectionConfig) -> None:
        self.cfg = cfg
        self.last_injected_text: str = ""
        self._last_hwnd: int = 0

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
        # Record the target window so scratch() can verify focus hasn't moved.
        self._last_hwnd = app_detect.foreground_hwnd()

    def scratch(self) -> int:
        """Delete the last injection by backspacing.

        Returns:
            N  — number of characters removed.
            0  — nothing to scratch.
            SCRATCH_WRONG_WINDOW (-1) — focus moved; refused.
        """
        text = self.last_injected_text
        if not text:
            return 0
        current = app_detect.foreground_hwnd()
        # If we don't know the original window (non-Windows / early failure),
        # or the user hasn't moved focus, proceed. Otherwise refuse — we can't
        # know where the backspaces would land.
        if self._last_hwnd and current and current != self._last_hwnd:
            return SCRATCH_WRONG_WINDOW

        for _ in range(len(text)):
            _keyboard.press(_Key.backspace)
            _keyboard.release(_Key.backspace)
            time.sleep(0.003)
        removed = len(text)
        self.last_injected_text = ""
        self._last_hwnd = 0
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
