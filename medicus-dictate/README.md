# Medicus Dictate

Local, Windows-native voice dictation for Medicus. Press a global hotkey, talk,
press again — transcription (via faster-whisper) is pasted into whatever field
has focus.

## Status

First delivery (steps 1–6 of the build plan): end-to-end dictation with tray UI.
Post-processing, PyInstaller packaging, and polish are deferred.

## Quick start

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
python -m src.transcriber    # transcribes out.wav and prints the text
```

## Configuration

Edit `config.toml` (see inline comments). The tray menu offers:

- *Show last transcription* — re-surface the most recent result.
- *Show last error* — useful when a dictation silently didn't land.
- *Quit*.

## Requirements

- Windows 10/11.
- Python 3.10+.
- Microphone permission granted to the terminal/app running it.
- First run downloads the Whisper model (`small.en`, ~470 MB).
