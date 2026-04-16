from __future__ import annotations

from typing import Iterable, Optional

import numpy as np

from .config import ModelConfig


class Transcriber:
    """Warm-loaded faster-whisper wrapper."""

    def __init__(self, cfg: ModelConfig) -> None:
        self.cfg = cfg
        self._model = None  # type: ignore[assignment]
        self._base_prompt: str = _build_initial_prompt(cfg.extra_vocabulary) if cfg.vocabulary_boost else ""

    def load(self) -> None:
        if self._model is not None:
            return
        # Imported lazily so the app can start up without CTranslate2 initialised
        # until the user actually reaches the transcription step.
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self.cfg.name,
            device=self.cfg.device,
            compute_type=self.cfg.compute_type,
        )

    def set_extra_vocabulary(self, terms: Iterable[str]) -> None:
        """Replace the per-call vocabulary bias — used by per-app profiles."""
        self._base_prompt = (
            _build_initial_prompt(list(terms)) if self.cfg.vocabulary_boost else ""
        )

    def transcribe(self, audio: np.ndarray, extra_prompt_terms: Optional[Iterable[str]] = None) -> str:
        if self._model is None:
            self.load()
        assert self._model is not None

        if audio.size == 0:
            return ""

        language: Optional[str] = self.cfg.language or None
        prompt = self._compose_prompt(extra_prompt_terms)

        # `.en` models are English-only; passing a language hint is redundant but harmless.
        segments, _info = self._model.transcribe(
            audio,
            language=language,
            vad_filter=True,
            beam_size=5,
            # Each dictation is a standalone utterance. Disabling the previous-
            # text condition dramatically reduces hallucination cascades
            # ("thank you for watching" / "please subscribe" artefacts) on
            # short clips with pauses.
            condition_on_previous_text=False,
            initial_prompt=prompt or None,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()

    def _compose_prompt(self, extra_terms: Optional[Iterable[str]]) -> str:
        if not self.cfg.vocabulary_boost:
            return ""
        if not extra_terms:
            return self._base_prompt
        merged = _build_initial_prompt(
            list(self.cfg.extra_vocabulary) + list(extra_terms)
        )
        # Merge the base prompt with the per-call terms, de-duplicated.
        return merged


def _build_initial_prompt(terms: Iterable[str]) -> str:
    """Build an initial_prompt string from vocabulary terms.

    Whisper uses the prompt as a style/context hint, not a strict word list,
    but mentioning uncommon terms up front measurably improves their
    recognition. We frame it as a neutral preceding sentence.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for t in terms:
        s = str(t).strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(s)
    if not ordered:
        return ""
    return "Clinical dictation. Vocabulary: " + ", ".join(ordered) + "."


def _selftest() -> None:
    """Transcribe out.wav. Run: python -m src.transcriber"""
    import wave
    from .config import load

    cfg = load()
    with wave.open("out.wav", "rb") as w:
        frames = w.readframes(w.getnframes())
        rate = w.getframerate()
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if rate != cfg.audio.sample_rate:
        raise RuntimeError(f"out.wav is {rate}Hz, config expects {cfg.audio.sample_rate}Hz")

    t = Transcriber(cfg.model)
    print("Loading model...")
    t.load()
    print("Transcribing...")
    print(repr(t.transcribe(audio)))


if __name__ == "__main__":
    _selftest()
