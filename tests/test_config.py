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
        groq_api_key: "gsk_test"
        hotkey: "right_alt"
        hold_or_toggle: "hold"
        scribe_keyterms: ["ElevenLabs"]
        cleanup_model: "llama-3.3-70b-versatile"
        cleanup_system_prompt_override: null
        max_recording_seconds: 45
    """)
    cfg = load_config(path)
    assert isinstance(cfg, Config)
    assert cfg.elevenlabs_api_key == "sk_eleven"
    assert cfg.groq_api_key == "gsk_test"
    assert cfg.cleanup_model == "llama-3.3-70b-versatile"
    assert cfg.scribe_keyterms == ["ElevenLabs"]
    assert cfg.max_recording_seconds == 45
    assert cfg.cleanup_system_prompt_override is None


def test_missing_elevenlabs_key_raises(tmp_path):
    path = write(tmp_path, """
        hotkey: "right_alt"
    """)
    with pytest.raises(ConfigError, match="elevenlabs_api_key"):
        load_config(path)


def test_missing_groq_key_raises(tmp_path):
    path = write(tmp_path, """
        elevenlabs_api_key: "sk_eleven"
    """)
    with pytest.raises(ConfigError, match="groq_api_key"):
        load_config(path)


def test_elevenlabs_placeholder_raises(tmp_path):
    path = write(tmp_path, """
        elevenlabs_api_key: "sk_replace_me"
        groq_api_key: "gsk_test"
    """)
    with pytest.raises(ConfigError, match="placeholder"):
        load_config(path)


def test_groq_placeholder_raises(tmp_path):
    path = write(tmp_path, """
        elevenlabs_api_key: "sk_eleven"
        groq_api_key: "gsk_replace_me"
    """)
    with pytest.raises(ConfigError, match="placeholder"):
        load_config(path)


def test_defaults_applied(tmp_path):
    path = write(tmp_path, """
        elevenlabs_api_key: "sk_eleven"
        groq_api_key: "gsk_test"
    """)
    cfg = load_config(path)
    assert cfg.hotkey == "right_alt"
    assert cfg.hold_or_toggle == "hold"
    assert cfg.scribe_keyterms == []
    assert cfg.cleanup_model == "llama-3.3-70b-versatile"
    assert cfg.max_recording_seconds == 60


def test_too_many_keyterms_raises(tmp_path):
    terms = "[" + ", ".join(f'"t{i}"' for i in range(101)) + "]"
    path = write(tmp_path, f"""
        elevenlabs_api_key: "sk_eleven"
        groq_api_key: "gsk_test"
        scribe_keyterms: {terms}
    """)
    with pytest.raises(ConfigError, match="100"):
        load_config(path)
