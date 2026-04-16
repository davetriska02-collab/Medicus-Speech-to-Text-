# Medicus Dictate

Local, Windows-native voice dictation for Medicus. Press a global hotkey, talk,
press again — the transcription (via local faster-whisper) is pasted at the
caret in whatever window has focus.

## Status

All nine plan steps implemented: config + recorder + transcriber + hotkey +
clipboard injection + tray UI + post-processing + PyInstaller build + polish.

## Quick start (dev)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m src
```

Press **Ctrl+Alt+Space** to start recording, press again to stop. The
transcription is pasted at the current caret.

## Self-tests

```powershell
python -m src.recorder       # records 5s, writes out.wav
python -m src.transcriber    # transcribes out.wav
python -m src.postprocess    # shows post-processing on sample phrases
```

## Packaging (Windows)

```powershell
pip install pyinstaller
python build.py
# -> dist/MedicusDictate.exe  +  dist/config.toml
```

The exe reads `config.toml` next to itself, so the clinician can edit it without
a rebuild. Windows Defender may flag the unsigned exe; signing is out of scope.

## Configuration

Edit `config.toml` (inline comments). Highlights:

- `[hotkey] combo` — pynput format, e.g. `<ctrl>+<alt>+<space>`.
- `[model] name` — `small.en` (default) or `medium.en`; `device = "cuda"` if a GPU is available.
- `[injection] mode` — `paste` (default) or `type` for fields that reject paste.
- `[postprocess]` — number-words→digits and unit abbreviations on by default;
  BNF frequency shorthand (`BD`, `TDS`, `nocte`, …) is opt-in.
- `[postprocess.custom]` — user-defined replacements for colleague names / drug
  brands that Whisper mangles.

## Tray feedback

- **Icon colour**: grey = idle, red = recording, amber = transcribing, teal = injecting.
- **Live level while recording**: the red disc's brightness pulses with mic RMS,
  and a white peak bar at the bottom of the icon rises with the loudest recent
  sample. If both stay flat while you're talking, your mic is off or routed
  wrong.
- **Silent-mic warning**: if 2s pass with no audible input after you press the
  hotkey, a toast tells you to check the mic.
- **Transcription errors** auto-surface as toasts when they happen.

Menu: *Show last transcription* · *Show last error* · *Quit*.

## Requirements

- Windows 10/11.
- Python 3.10+ (only for dev; the packaged exe has no Python dependency).
- Microphone permission granted to the app/terminal.
- First run downloads the Whisper model (`small.en`, ~470 MB) to the
  HuggingFace cache.
