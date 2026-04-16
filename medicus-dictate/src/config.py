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
class Config:
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    injection: InjectionConfig = field(default_factory=InjectionConfig)
    postprocess: PostprocessConfig = field(default_factory=PostprocessConfig)
    commands: CommandsConfig = field(default_factory=CommandsConfig)
    smart: SmartConfig = field(default_factory=SmartConfig)


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
    if cfg.smart.mode not in ("off", "rules", "ollama"):
        raise ValueError(f"smart.mode must be 'off', 'rules' or 'ollama', got {cfg.smart.mode}")
