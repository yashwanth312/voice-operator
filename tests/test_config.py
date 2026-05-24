import textwrap
import pytest
from voice_operator.config import Config, load_config, ConfigError


def write(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return p


def test_loads_valid_config(tmp_path):
    path = write(tmp_path, """
        elevenlabs_api_key: "sk_eleven"
        hotkey: "right_alt"
        hold_or_toggle: "hold"
        scribe_keyterms: ["Anthropic", "ElevenLabs"]
        cleanup_model: "claude-haiku-4-5"
        cleanup_system_prompt_override: null
        max_recording_seconds: 45
    """)
    cfg = load_config(path)
    assert isinstance(cfg, Config)
    assert cfg.elevenlabs_api_key == "sk_eleven"
    assert cfg.cleanup_model == "claude-haiku-4-5"
    assert cfg.scribe_keyterms == ["Anthropic", "ElevenLabs"]
    assert cfg.max_recording_seconds == 45
    assert cfg.cleanup_system_prompt_override is None


def test_missing_required_key_raises(tmp_path):
    path = write(tmp_path, """
        hotkey: "right_alt"
    """)
    with pytest.raises(ConfigError, match="elevenlabs_api_key"):
        load_config(path)


def test_placeholder_key_raises(tmp_path):
    path = write(tmp_path, """
        elevenlabs_api_key: "sk_replace_me"
    """)
    with pytest.raises(ConfigError, match="placeholder"):
        load_config(path)


def test_defaults_applied(tmp_path):
    path = write(tmp_path, """
        elevenlabs_api_key: "sk_eleven"
    """)
    cfg = load_config(path)
    assert cfg.hotkey == "right_alt"
    assert cfg.hold_or_toggle == "hold"
    assert cfg.scribe_keyterms == []
    assert cfg.cleanup_model == "claude-haiku-4-5"
    assert cfg.max_recording_seconds == 60


def test_too_many_keyterms_raises(tmp_path):
    terms = "[" + ", ".join(f'"t{i}"' for i in range(101)) + "]"
    path = write(tmp_path, f"""
        elevenlabs_api_key: "sk_eleven"
        scribe_keyterms: {terms}
    """)
    with pytest.raises(ConfigError, match="100"):
        load_config(path)
