from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def _default_config_path() -> Path:
    # When frozen by PyInstaller, look next to the executable so the user can
    # edit config.toml without rebuilding. Dev runs look one level above src/.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config.toml"
    return Path(__file__).resolve().parent.parent / "config.toml"


DEFAULT_CONFIG_PATH = _default_config_path()


@dataclass
class HotkeyConfig:
    combo: str = "<ctrl>+<alt>+<space>"
    # Tap (short press) toggles recording; hold-beyond-threshold is
    # push-to-talk (record while held, stop on release).
    hold_threshold_ms: int = 300


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    device: Optional[int] = None
    # Short tick when the mic opens so the clinician knows it's live.
    start_cue_enabled: bool = True


@dataclass
class ModelConfig:
    name: str = "small.en"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"
    # Whisper's initial_prompt biases recognition toward terms it expects.
    # We seed it from the custom dictionary and any extra terms listed
    # under model.extra_vocabulary.
    vocabulary_boost: bool = True
    extra_vocabulary: list = field(default_factory=list)


@dataclass
class InjectionConfig:
    mode: str = "paste"
    pre_delay_ms: int = 50


@dataclass
class PostprocessConfig:
    enable_number_words: bool = True
    enable_unit_abbrev: bool = True
    enable_bnf_frequencies: bool = False
    custom: dict = field(default_factory=dict)


@dataclass
class CommandsConfig:
    enabled: bool = True


@dataclass
class SmartConfig:
    # "off" | "rules" | "ollama". Ollama is LOCAL-only (loopback / private IP).
    mode: str = "rules"
    ollama_endpoint: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_s: float = 8.0
    ollama_fallback_to_rules: bool = True


@dataclass
class HistoryConfig:
    # Size of the last-N-utterances ring buffer surfaced in the tray menu.
    size: int = 5


@dataclass
class TTSConfig:
    # "Read last" menu item and the "read that back" voice command use SAPI
    # via pyttsx3 (local). Rate is SAPI words-per-minute; voice name is the
    # SAPI voice ID (leave empty for system default).
    enabled: bool = True
    rate: int = 180
    voice: str = ""


@dataclass
class Config:
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    injection: InjectionConfig = field(default_factory=InjectionConfig)
    postprocess: PostprocessConfig = field(default_factory=PostprocessConfig)
    commands: CommandsConfig = field(default_factory=CommandsConfig)
    smart: SmartConfig = field(default_factory=SmartConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    # Per-app profiles: {exe_name_lowercase: {"custom": {...}, "enable_bnf_frequencies": bool}}.
    # Populated from [[profiles]] in config.toml.
    profiles: dict = field(default_factory=dict)


def load(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    cfg = Config(
        hotkey=HotkeyConfig(**data.get("hotkey", {})),
        audio=AudioConfig(**data.get("audio", {})),
        model=ModelConfig(**data.get("model", {})),
        injection=InjectionConfig(**data.get("injection", {})),
        postprocess=PostprocessConfig(**data.get("postprocess", {})),
        commands=CommandsConfig(**data.get("commands", {})),
        smart=SmartConfig(**data.get("smart", {})),
        history=HistoryConfig(**data.get("history", {})),
        tts=TTSConfig(**data.get("tts", {})),
        profiles=_load_profiles(data.get("profiles", [])),
    )
    _validate(cfg)
    return cfg


def _load_profiles(raw) -> dict:
    """Normalise [[profiles]] into {exe_lower: {...overrides...}}.

    Each profile entry in config.toml looks like:
        [[profiles]]
        exe = "emis.exe"
        enable_bnf_frequencies = true
        custom = { "bp" = "blood pressure" }
    """
    out: dict = {}
    if not isinstance(raw, list):
        return out
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        exe = str(entry.get("exe", "")).strip().lower()
        if not exe:
            continue
        overrides = {k: v for k, v in entry.items() if k != "exe"}
        out[exe] = overrides
    return out


def _validate(cfg: Config) -> None:
    if cfg.audio.sample_rate not in (8000, 16000, 22050, 32000, 44100, 48000):
        raise ValueError(f"Unsupported sample_rate: {cfg.audio.sample_rate}")
    if cfg.audio.channels not in (1, 2):
        raise ValueError(f"channels must be 1 or 2, got {cfg.audio.channels}")
    if cfg.model.device not in ("cpu", "cuda"):
        raise ValueError(f"model.device must be 'cpu' or 'cuda', got {cfg.model.device}")
    if cfg.injection.mode not in ("paste", "type"):
        raise ValueError(f"injection.mode must be 'paste' or 'type', got {cfg.injection.mode}")
    if cfg.smart.mode not in ("off", "rules", "ollama"):
        raise ValueError(f"smart.mode must be 'off', 'rules' or 'ollama', got {cfg.smart.mode}")
