from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_PLACEHOLDERS = {"sk_replace_me", "sk_eleven_replace_me"}
_DEFAULT_CLEANUP_MODEL = "claude-haiku-4-5"


class ConfigError(Exception):
    pass


@dataclass
class Config:
    elevenlabs_api_key: str
    hotkey: str = "right_alt"
    hold_or_toggle: str = "hold"
    scribe_keyterms: list[str] = field(default_factory=list)
    cleanup_model: str = _DEFAULT_CLEANUP_MODEL
    cleanup_system_prompt_override: str | None = None
    max_recording_seconds: int = 60


def default_config_path() -> Path:
    base = os.environ.get("APPDATA", str(Path.home()))
    return Path(base) / "voice-operator" / "config.yaml"


def load_config(path: Path | None = None) -> Config:
    path = path or default_config_path()
    if not path.exists():
        raise ConfigError(
            f"No config at {path}. Copy config.example.yaml there and fill in your key."
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    value = data.get("elevenlabs_api_key")
    if not value:
        raise ConfigError("Missing required config key: elevenlabs_api_key")
    if value in _PLACEHOLDERS:
        raise ConfigError("Config key elevenlabs_api_key still holds a placeholder value.")

    keyterms = data.get("scribe_keyterms") or []
    if len(keyterms) > 100:
        raise ConfigError("scribe_keyterms may contain at most 100 terms.")

    return Config(
        elevenlabs_api_key=value,
        hotkey=data.get("hotkey", "right_alt"),
        hold_or_toggle=data.get("hold_or_toggle", "hold"),
        scribe_keyterms=keyterms,
        cleanup_model=data.get("cleanup_model") or _DEFAULT_CLEANUP_MODEL,
        cleanup_system_prompt_override=data.get("cleanup_system_prompt_override"),
        max_recording_seconds=int(data.get("max_recording_seconds", 60)),
    )
