"""Rules-based clean-up applied to Whisper output before injection.

Each rule is opt-in via config. The custom dictionary runs last, so it can
override anything the earlier rules produced.
"""
from __future__ import annotations

import re
from typing import Dict

from .config import PostprocessConfig


_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_SCALES = {"hundred": 100, "thousand": 1000}

_NUM_WORDS = set(_UNITS) | set(_TENS) | set(_SCALES)

_UNIT_ABBREV = [
    (r"\bmilligrams?\b", "mg"),
    (r"\bmicrograms?\b", "mcg"),
    (r"\bmillilitres?\b", "ml"),
    (r"\bmilliliters?\b", "ml"),
    (r"\bkilograms?\b", "kg"),
    (r"\bgrams?\b", "g"),
]

_BNF_FREQ = [
    (r"\bonce\s+daily\b", "OD"),
    (r"\btwice\s+daily\b", "BD"),
    (r"\bthree\s+times\s+a\s+day\b", "TDS"),
    (r"\bthree\s+times\s+daily\b", "TDS"),
    (r"\bfour\s+times\s+a\s+day\b", "QDS"),
    (r"\bfour\s+times\s+daily\b", "QDS"),
    (r"\bat\s+night\b", "nocte"),
    (r"\bin\s+the\s+morning\b", "mane"),
    (r"\bas\s+required\b", "PRN"),
    (r"\bwhen\s+required\b", "PRN"),
]


def _parse_number_words(words: list[str]) -> int:
    total = 0
    current = 0
    for w in words:
        if w in _UNITS:
            current += _UNITS[w]
        elif w in _TENS:
            current += _TENS[w]
        elif w == "hundred":
            current = (current or 1) * 100
        elif w == "thousand":
            current = (current or 1) * 1000
            total += current
            current = 0
    return total + current


def _replace_number_words(text: str) -> str:
    # Find contiguous runs of number words (whitespace and "and" allowed as
    # connectors) and replace each run with the equivalent digit.
    words = list(re.finditer(r"[A-Za-z]+", text))
    parts: list[str] = []
    last_end = 0
    i = 0
    while i < len(words):
        if words[i].group().lower() not in _NUM_WORDS:
            i += 1
            continue
        run_tokens = [words[i].group().lower()]
        run_start = words[i].start()
        run_end = words[i].end()
        j = i + 1
        while j < len(words):
            between = text[run_end:words[j].start()]
            if not re.fullmatch(r"\s*", between):
                break
            word = words[j].group().lower()
            if word in _NUM_WORDS:
                run_tokens.append(word)
                run_end = words[j].end()
                j += 1
            elif (
                word == "and"
                and j + 1 < len(words)
                and words[j + 1].group().lower() in _NUM_WORDS
                and re.fullmatch(r"\s*", text[words[j].end():words[j + 1].start()])
            ):
                # Consume the "and" connector; the next iteration picks up the number.
                run_end = words[j].end()
                j += 1
            else:
                break
        parts.append(text[last_end:run_start])
        parts.append(str(_parse_number_words(run_tokens)))
        last_end = run_end
        i = j
    parts.append(text[last_end:])
    return "".join(parts)


def _replace_units(text: str) -> str:
    for pat, repl in _UNIT_ABBREV:
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text


def _replace_bnf(text: str) -> str:
    for pat, repl in _BNF_FREQ:
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text


def _apply_custom(text: str, custom: Dict[str, str]) -> str:
    for src, dst in custom.items():
        # Whole-phrase, case-insensitive.
        text = re.sub(rf"\b{re.escape(src)}\b", dst, text, flags=re.IGNORECASE)
    return text


def process(text: str, cfg: PostprocessConfig) -> str:
    if not text:
        return text
    # BNF first so multi-word frequency phrases ("three times daily") match
    # before their leading number word gets converted to a digit.
    if cfg.enable_bnf_frequencies:
        text = _replace_bnf(text)
    if cfg.enable_unit_abbrev:
        text = _replace_units(text)
    if cfg.enable_number_words:
        text = _replace_number_words(text)
    if cfg.custom:
        text = _apply_custom(text, cfg.custom)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return text


if __name__ == "__main__":
    from .config import load
    cfg = load()
    samples = [
        "give two hundred milligrams twice daily",
        "take fifty micrograms once daily",
        "three thousand units please",
    ]
    for s in samples:
        print(f"{s!r} -> {process(s, cfg.postprocess)!r}")
