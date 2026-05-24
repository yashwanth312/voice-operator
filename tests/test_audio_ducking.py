from voice_operator.audio_ducking import should_skip_session


def test_skips_comm_apps():
    assert should_skip_session("Teams.exe") is True
    assert should_skip_session("zoom.exe") is True
    assert should_skip_session("Discord.exe") is True


def test_skips_own_process():
    assert should_skip_session("python.exe") is True


def test_does_not_skip_media_apps():
    assert should_skip_session("Spotify.exe") is False
    assert should_skip_session("chrome.exe") is False
