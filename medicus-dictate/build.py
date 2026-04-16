"""Build a single-file Windows .exe for Medicus Dictate.

Usage:
    python build.py

Output:
    dist/MedicusDictate.exe
    dist/config.toml         (copied so the user can edit it next to the exe)

Notes:
    - Run on Windows with `pyinstaller` already installed (`pip install pyinstaller`).
    - faster-whisper / CTranslate2 ship a bundled model loader; the .exe will
      download the Whisper model on first run to the user's HuggingFace cache.
    - Windows Defender may flag unsigned PyInstaller exes. Signing is out of
      scope for this delivery.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "MedicusDictate.spec"


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> int:
    if sys.platform != "win32":
        print(f"Warning: building on {sys.platform}; the produced artifact will not run on Windows.")

    # Clean previous outputs so stale builds don't masquerade as success.
    for p in (DIST, BUILD):
        if p.exists():
            shutil.rmtree(p)
    if SPEC.exists():
        SPEC.unlink()

    _run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",                    # no console window on Windows
        "--name", "MedicusDictate",
        "--collect-submodules", "faster_whisper",
        "--collect-submodules", "pystray",
        "--collect-submodules", "PIL",
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse._win32",
        str(ROOT / "src" / "__main__.py"),
    ])

    # Copy the default config next to the exe so first-run users have something to edit.
    shipped_config = DIST / "config.toml"
    shutil.copyfile(ROOT / "config.toml", shipped_config)

    print()
    print(f"Built: {DIST / 'MedicusDictate.exe'}")
    print(f"Config: {shipped_config}  (edit to taste)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
