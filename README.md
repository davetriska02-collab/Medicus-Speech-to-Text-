# Medicus Dictate

**Local voice dictation for clinical work on Windows.** Press a hotkey, talk, and
your words appear wherever your cursor is — EMIS, SystmOne, Vision, Outlook, any
text field.

Everything runs on your PC. No cloud, no account, no subscription.
Patient-identifiable text never leaves the machine.

Landing page with screenshots and setup walk-through:
**[medicus-dictate landing page](https://davetriska02-collab.github.io/Medicus-Speech-to-Text-/)**
(once GitHub Pages is enabled for this repo — see [hosting the page](#hosting-the-landing-page) below).

## What you get

- Global hotkey: tap to toggle recording, **hold** for push-to-talk.
- Tray icon that **pulses with your voice level** so you can see the mic is live.
- **Voice commands** for punctuation, new lines, capitalisation, "scratch that"
  to undo, "read that back" to hear the last dictation.
- **Medical post-processing**: "fifty micrograms once daily" → "50 mcg OD",
  optional BNF shorthand, custom dictionaries, grammar tidy.
- **Vocabulary boost**: bias Whisper toward your drug names, colleague names,
  local surgery names.
- **Per-app profiles**: different vocabulary and formatting rules for EMIS,
  SystmOne, Outlook, etc.
- Runs on your PC: Whisper (faster-whisper) does the transcription locally.
  Optional grammar tidy via a **local** Ollama endpoint — the app refuses any
  non-private IP.

## Getting it running

There's no one-click installer yet. You'll need Python 3.10+ installed from
[python.org](https://www.python.org/downloads/). About five minutes of setup.

```powershell
git clone https://github.com/davetriska02-collab/Medicus-Speech-to-Text-
cd Medicus-Speech-to-Text-/medicus-dictate
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m src
```

Press **Ctrl + Alt + Space** to start recording, press again to stop. First run
downloads the Whisper model (~470 MB) — one-off.

Full technical documentation lives in [medicus-dictate/README.md](medicus-dictate/README.md).

## Building a standalone .exe (optional)

There is currently **no pre-built release** — a packaged `.exe` is not attached
to the repo. If you want one, you can build it yourself:

```powershell
pip install pyinstaller
python build.py
```

The resulting `dist/MedicusDictate.exe` runs without Python installed. Note that
Windows Defender may flag unsigned PyInstaller binaries.

## Hosting the landing page

The HTML landing page is ready under `docs/`. To publish it at
`davetriska02-collab.github.io/Medicus-Speech-to-Text-`:

1. Repo Settings → Pages.
2. Source: *Deploy from a branch*.
3. Branch: `main` (or the default), folder: `/docs`.
4. Save. The page is live within a minute.

## Privacy at a glance

- No audio, text, or telemetry leaves your computer.
- No account, no login, no API key.
- No analytics, no crash reporting.
- Open source and auditable — no obfuscated binaries.

## Licence

See [LICENSE](LICENSE) once added. Pre-release; use at your own risk.
