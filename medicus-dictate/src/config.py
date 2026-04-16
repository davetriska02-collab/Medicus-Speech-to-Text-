from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"


@dataclass
class HotkeyConfig:
    combo: str = "<ctrl>+<alt>+<space>"


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    device: Optional[int] = None


@dataclass
class ModelConfig:
    name: str = "small.en"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"


@dataclass
class InjectionConfig:
    mode: str = "paste"
    pre_delay_ms: int = 50


@dataclass
class PostprocessConfig:
    enable_number_words: bool = False
    enable_unit_abbrev: bool = False
    enable_bnf_frequencies: bool = False


@dataclass
class Config:
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    injection: InjectionConfig = field(default_factory=InjectionConfig)
    postprocess: PostprocessConfig = field(default_factory=PostprocessConfig)


def load(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    cfg = Config(
        hotkey=HotkeyConfig(**data.get("hotkey", {})),
        audio=AudioConfig(**data.get("audio", {})),
        model=ModelConfig(**data.get("model", {})),
        injection=InjectionConfig(**data.get("injection", {})),
        postprocess=PostprocessConfig(**data.get("postprocess", {})),
    )
    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    if cfg.audio.sample_rate not in (8000, 16000, 22050, 32000, 44100, 48000):
        raise ValueError(f"Unsupported sample_rate: {cfg.audio.sample_rate}")
    if cfg.audio.channels not in (1, 2):
        raise ValueError(f"channels must be 1 or 2, got {cfg.audio.channels}")
    if cfg.model.device not in ("cpu", "cuda"):
        raise ValueError(f"model.device must be 'cpu' or 'cuda', got {cfg.model.device}")
    if cfg.injection.mode not in ("paste", "type"):
        raise ValueError(f"injection.mode must be 'paste' or 'type', got {cfg.injection.mode}")
