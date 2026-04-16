"""Smart-dictate tidy pass — runs after voice_commands + postprocess.

Modes (selected by config, all local-only):
    off    — no tidy, pass through.
    rules  — regex cleanup (whitespace, punctuation, sentence caps, i→I).
    ollama — query a LOCAL Ollama endpoint for grammar clean-up, with a
             rules-mode fallback if the endpoint is unreachable.

The Ollama path refuses any endpoint that resolves to a non-loopback /
non-private IP. A clinical dictation tool must not leak patient-identifiable
text to a public service via mis-configuration.
"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

from .config import SmartConfig


# ---------------------------------------------------------------- rules mode

def _rules_tidy(text: str) -> str:
    if not text:
        return text

    # 1. Normalise whitespace around punctuation and newlines.
    # Drop spaces before closing punctuation.
    text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
    # Ensure a single space after a sentence punct when followed by a letter/digit.
    text = re.sub(r"([,.;:!?])(?=[A-Za-z0-9])", r"\1 ", text)
    # Spaces around newlines: drop them so voice-command newlines don't leave gaps.
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)

    # 2. Collapse consecutive duplicate punctuation ("..", ",,", "??").
    text = re.sub(r"([,.;:!?])\1+", r"\1", text)

    # 3. "i" pronoun — standalone, lower-case, becomes "I". Contractions
    # like "i'm" / "i'll" / "i've" also get their leading "i" capitalised.
    text = re.sub(r"(?<![A-Za-z'])i(?![A-Za-z])", "I", text)

    # 4. Capitalise the first alphabetic character of each sentence. A sentence
    # starts at the beginning of the text, after a terminal punctuation mark
    # plus whitespace, or after a newline.
    def _cap(m: re.Match) -> str:
        prefix, ch = m.group(1), m.group(2)
        return prefix + ch.upper()

    text = re.sub(r"(^|[.!?]\s+|\n+[ \t]*)([a-z])", _cap, text)

    # 5. Collapse runs of spaces (but not newlines).
    text = re.sub(r"[ \t]{2,}", " ", text)

    # 6. Strip trailing whitespace on each line and leading/trailing overall.
    text = "\n".join(line.rstrip() for line in text.split("\n")).strip()
    return text


# --------------------------------------------------------------- ollama mode

class OllamaUnavailable(Exception):
    pass


_PROMPT = (
    "You are a medical transcription editor. Fix only grammar, punctuation, "
    "capitalisation, and obvious word-level typos in the clinical dictation "
    "below. You MUST preserve every clinical term, drug name, dose, unit, "
    "and abbreviation exactly as written (e.g. mg, mcg, BD, TDS, PRN, mane, "
    "nocte). Do NOT rephrase, add commentary, or reorder ideas. Return only "
    "the corrected text, nothing else.\n\n"
    "Dictation:\n{text}\n\n"
    "Corrected:"
)


def _assert_local_endpoint(endpoint: str) -> None:
    """Refuse any endpoint that isn't on loopback / a private IP range.

    This is a safety belt: a clinical user who mis-types the endpoint in
    config.toml should get a failure, not silent exfiltration of patient text.
    """
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.hostname
    if not host:
        raise OllamaUnavailable(f"Ollama endpoint has no host: {endpoint!r}")
    if host in ("localhost", "ip6-localhost", "ip6-loopback"):
        return
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Resolve a name. Only accept if it maps to a private/loopback IP.
        try:
            resolved = socket.gethostbyname(host)
        except socket.gaierror as e:
            raise OllamaUnavailable(f"Could not resolve Ollama host {host!r}: {e}") from e
        ip = ipaddress.ip_address(resolved)
    if ip.is_loopback or ip.is_private or ip.is_link_local:
        return
    raise OllamaUnavailable(
        f"Ollama endpoint {endpoint!r} resolves to a non-private IP ({ip}); "
        "refusing to send clinical text to a public address."
    )


def _ollama_tidy(text: str, cfg: SmartConfig) -> str:
    _assert_local_endpoint(cfg.ollama_endpoint)
    body = json.dumps({
        "model": cfg.ollama_model,
        "prompt": _PROMPT.format(text=text),
        "stream": False,
        "options": {"temperature": 0.0},
    }).encode("utf-8")
    req = urllib.request.Request(
        cfg.ollama_endpoint.rstrip("/") + "/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.ollama_timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        raise OllamaUnavailable(f"Ollama request failed: {e}") from e

    result = str(payload.get("response", "")).strip()
    if not result:
        raise OllamaUnavailable("Ollama returned an empty response.")
    return result


# ------------------------------------------------------------------ dispatch

def tidy(text: str, cfg: SmartConfig) -> str:
    if cfg.mode == "off" or not text:
        return text
    if cfg.mode == "rules":
        return _rules_tidy(text)
    if cfg.mode == "ollama":
        try:
            return _ollama_tidy(text, cfg)
        except OllamaUnavailable as e:
            if cfg.ollama_fallback_to_rules:
                print(f"[smart] ollama unavailable, falling back to rules: {e}")
                return _rules_tidy(text)
            raise
    # Unknown mode — config validation should have caught this.
    return text


if __name__ == "__main__":
    from .config import SmartConfig as _S
    cfg = _S(mode="rules")
    cases = [
        "the patient was admitted . \n\nthe chart shows BP of 120 over 80",
        "hello , how are you ?",
        "i was there",
        "they wrote  multiple   spaces  ,,  and misplaced .. punctuation",
    ]
    for s in cases:
        print(f"{s!r}\n  -> {tidy(s, cfg)!r}\n")
