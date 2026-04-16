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
- `[commands] enabled` — voice commands for punctuation / newlines / case.
- `[smart] mode` — `off` / `rules` / `ollama` for grammar clean-up.
- `[postprocess]` — number-words→digits and unit abbreviations on by default;
  BNF frequency shorthand (`BD`, `TDS`, `nocte`, …) is opt-in.
- `[postprocess.custom]` — user-defined replacements for colleague names / drug
  brands that Whisper mangles.

## Voice commands

When `[commands] enabled = true` these spoken phrases become formatting
rather than literal text:

| Say | Get |
|---|---|
| `new line` | newline |
| `new paragraph` | blank-line break |
| `full stop` | `.` |
| `comma` | `,` |
| `question mark` / `exclamation mark` | `?` / `!` |
| `semicolon` | `;` |
| `open bracket` / `close bracket` | `(` / `)` |
| `open quote` / `close quote` | `"` |
| `hyphen` | `-` |
| `capitalise next <word>` or `cap next <word>` | title-cases the next word |
| `caps on` … `caps off` | upper-cases the span between |

`"period"` and `"colon"` are deliberately **not** commands — they clash with
the menstrual/temporal "period" and anatomical "colon" in clinical dictation.
Use `full stop` for `.` and type the colon literally.

## Smart-dictate mode

`[smart] mode` controls post-transcription grammar / formatting clean-up.
All three options are **local-only**. No cloud APIs.

- `off` — no tidy; raw Whisper output (plus voice commands + medical
  postprocess) goes straight to the caret.
- `rules` (default) — regex pass: sentence capitalisation, `i`/`i'm` → `I`/`I'm`,
  punctuation spacing, collapse double-spaces, dedupe `,,` / `..`. Zero external
  deps.
- `ollama` — sends the draft to a local [Ollama](https://ollama.com) endpoint
  for grammar tidy (`llama3.2:3b` default). The app **refuses** any endpoint
  that resolves to a non-loopback / non-private IP, so a mis-typed config
  can't accidentally exfiltrate patient-identifiable text. Falls back to
  `rules` if Ollama is unreachable.

## Known deployment concerns

- Windows **clipboard history** (Win+V) captures every paste — including
  dictated patient-identifiable text — when paste-mode injection is used.
  Until we mark our clipboard writes with `CF_EXCLUDEFROMCLIPBOARDHISTORY`,
  disable clipboard history on clinical workstations, or switch
  `[injection] mode` to `"type"`.
- Windows UIPI: if Medicus runs elevated and this app doesn't, paste/type
  can't reach Medicus's windows. Run both at the same privilege level.

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
