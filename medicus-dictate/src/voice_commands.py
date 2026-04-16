"""Voice-command processing.

Runs between Whisper and the medical postprocess. Converts spoken phrases
like "new line", "full stop", "caps on ... caps off" into actual punctuation,
newlines, and case changes. No cloud dependency.

Pipeline order (in __main__._process):
    Whisper -> voice_commands.apply -> postprocess -> smart.tidy -> inject
"""
from __future__ import annotations

import re
from typing import List, Tuple

# (pattern, replacement) — first match wins, so order longer phrases first
# so "new paragraph" matches before "new line".
# Command list is deliberately conservative for clinical use:
#   "period" is EXCLUDED — clashes with menstrual/temporal sense.
#   "colon" is EXCLUDED — clashes with anatomy.
#   Use "full stop" for '.' and a literal ':' if you need one.
_SIMPLE_COMMANDS: List[Tuple[str, str]] = [
    (r"\bnew\s+paragraph\b", "\n\n"),
    (r"\bnew\s+line\b", "\n"),
    (r"\bfull\s+stop\b", "."),
    (r"\bquestion\s+mark\b", "?"),
    (r"\bexclamation\s+mark\b", "!"),
    (r"\bexclamation\s+point\b", "!"),
    (r"\bcomma\b", ","),
    (r"\bsemicolon\b", ";"),
    (r"\bopen\s+bracket\b", "("),
    (r"\bclose\s+bracket\b", ")"),
    (r"\bopen\s+parenthesis\b", "("),
    (r"\bclose\s+parenthesis\b", ")"),
    (r"\bopen\s+quote\b", '"'),
    (r"\bclose\s+quote\b", '"'),
    (r"\bhyphen\b", "-"),
]

_CAPS_ON = re.compile(r"\b(?:all\s+caps\s+on|caps\s+on)\b", re.IGNORECASE)
_CAPS_OFF = re.compile(r"\b(?:all\s+caps\s+off|caps\s+off)\b", re.IGNORECASE)
# "capitalise next" / "capitalize next" / "cap next" — title-case the next word.
# Bare "cap" is intentionally NOT accepted because it's a real English word
# (e.g. "he wore a cap") and the false-positive rate is unacceptably high.
_CAP_NEXT = re.compile(
    r"\b(?:capitalise\s+next|capitalize\s+next|cap\s+next)\b\s*",
    re.IGNORECASE,
)


def apply(text: str) -> str:
    if not text:
        return text
    # 1. Caps-on / caps-off spans → upper-case the content between them.
    text = _apply_caps_spans(text)
    # 2. Cap-next markers → title-case the following word.
    text = _apply_cap_next(text)
    # 3. Simple phrase → token substitutions.
    for pattern, replacement in _SIMPLE_COMMANDS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _apply_caps_spans(text: str) -> str:
    """Upper-case content between matching 'caps on' and 'caps off' markers.

    If 'caps on' is unmatched at end of input, upper-case to EOF.
    """
    out: List[str] = []
    pos = 0
    while pos < len(text):
        m_on = _CAPS_ON.search(text, pos)
        if m_on is None:
            out.append(text[pos:])
            break
        out.append(text[pos:m_on.start()])
        m_off = _CAPS_OFF.search(text, m_on.end())
        if m_off is None:
            out.append(text[m_on.end():].upper())
            pos = len(text)
        else:
            out.append(text[m_on.end():m_off.start()].upper())
            pos = m_off.end()
    return "".join(out)


def _apply_cap_next(text: str) -> str:
    """Title-case the word following a 'capitalise next' / 'cap next' marker.

    Only upper-cases the first letter — the rest of the word is left untouched
    so that a word already upper-cased (e.g. from inside a `caps on ... caps
    off` span) isn't stomped back to mixed case.
    """
    out: List[str] = []
    pos = 0
    while True:
        m = _CAP_NEXT.search(text, pos)
        if m is None:
            out.append(text[pos:])
            break
        out.append(text[pos:m.start()])
        tail = text[m.end():]
        wm = re.match(r"(\s*)([A-Za-z][A-Za-z']*)", tail)
        if wm is None:
            # No following word — drop the marker entirely.
            pos = m.end()
            continue
        leading, word = wm.group(1), wm.group(2)
        out.append(leading + word[:1].upper() + word[1:])
        pos = m.end() + wm.end()
    return "".join(out)


if __name__ == "__main__":
    samples = [
        "the patient was admitted new paragraph the chart shows caps on bp caps off of 120 over 80",
        "hello comma how are you question mark",
        "cap john smith was here",
        "take two tablets new line twice daily",
    ]
    for s in samples:
        print(f"{s!r}\n  -> {apply(s)!r}\n")
