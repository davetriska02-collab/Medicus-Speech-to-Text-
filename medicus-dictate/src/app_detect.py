"""Foreground-application detection for per-app profiles.

Windows-only: uses ctypes against user32/kernel32 so we don't pull in pywin32.
Non-Windows returns ""/0 — profiles never match and focus-safety checks are
trivially satisfied.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

_IS_WIN = sys.platform == "win32"

# Lazily bound Win32 functions with explicit argtypes/restype. Declaring
# these up front matters on 64-bit Python: HWND and HANDLE are pointer-sized,
# and ctypes defaults to c_int which silently truncates. Binding once avoids
# re-declaring on every call.
_bound = False


def _bind() -> bool:
    """Declare the Win32 signatures we need. Idempotent; no-op off Windows."""
    global _bound, _user32, _kernel32
    if _bound:
        return True
    if not _IS_WIN:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32
        k = ctypes.windll.kernel32

        u.GetForegroundWindow.restype = wintypes.HWND
        u.GetForegroundWindow.argtypes = []

        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]

        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

        k.CloseHandle.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]

        k.QueryFullProcessImageNameW.restype = wintypes.BOOL
        k.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]

        _user32 = u
        _kernel32 = k
        _bound = True
        return True
    except Exception:
        return False


def foreground_hwnd() -> int:
    """Return the foreground HWND as an int, or 0 if none / not Windows."""
    if not _bind():
        return 0
    try:
        hwnd = _user32.GetForegroundWindow()
        return int(hwnd) if hwnd else 0
    except Exception:
        return 0


def _exe_for_hwnd(hwnd: int) -> str:
    if not hwnd or not _bind():
        return ""
    try:
        import ctypes
        from ctypes import wintypes

        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000 — minimum rights to read
        # the image filename without needing debug privilege.
        handle = _kernel32.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            ok = _kernel32.QueryFullProcessImageNameW(
                handle, 0, buf, ctypes.byref(size)
            )
            if not ok:
                return ""
            return os.path.basename(buf.value).lower()
        finally:
            _kernel32.CloseHandle(handle)
    except Exception:
        return ""


def foreground_exe_name() -> str:
    """Lowercase executable basename of the foreground window, or ''."""
    return _exe_for_hwnd(foreground_hwnd())
