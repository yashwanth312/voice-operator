import os
import pathlib

import pytest
import yaml

from voice_operator.cleanup import build_system_prompt, BUNDLED_PROMPT, polish
from voice_operator.context import AppContext


def test_prompt_includes_app_context():
    prompt = build_system_prompt(AppContext("Slack", "general"), override=None)
    assert "Slack" in prompt
    assert "general" in prompt
    assert "filler" in prompt.lower()


def test_override_replaces_bundled_body_but_keeps_context():
    prompt = build_system_prompt(AppContext("VS Code", "main.py"), override="CUSTOM RULES")
    assert "CUSTOM RULES" in prompt
    assert "VS Code" in prompt
    assert "main.py" in prompt


def test_bundled_prompt_has_core_guardrails():
    assert "NEVER add information" in BUNDLED_PROMPT
    assert "NEVER reorganize or summarize" in BUNDLED_PROMPT


def _load_fixtures():
    path = pathlib.Path(__file__).parent / "fixtures" / "transcripts.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.integration
@pytest.mark.parametrize("case", _load_fixtures())
async def test_cleanup_golden(case):
    # Guard: this must run on the Max subscription, never an API key.
    os.environ.pop("ANTHROPIC_API_KEY", None)
    out = await polish(case["raw"], AppContext(case["app"], ""))
    for needle in case["expected_contains"]:
        assert needle in out, f"{needle!r} missing from: {out!r}"
    for bad in case["expected_excludes"]:
        assert bad not in out, f"{bad!r} should not be in: {out!r}"
