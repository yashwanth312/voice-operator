import json
from voice_operator.stt import parse_message, Transcript


def test_parse_partial():
    msg = json.dumps({"type": "partial_transcript", "text": "hello wor"})
    t = parse_message(msg)
    assert t == Transcript(text="hello wor", is_final=False)


def test_parse_committed():
    msg = json.dumps({"type": "committed_transcript", "text": "hello world"})
    t = parse_message(msg)
    assert t == Transcript(text="hello world", is_final=True)


def test_parse_session_started_returns_none():
    assert parse_message(json.dumps({"type": "session_started"})) is None


def test_parse_unknown_returns_none():
    assert parse_message(json.dumps({"type": "something_else"})) is None


def test_parse_malformed_returns_none():
    assert parse_message("not json") is None
