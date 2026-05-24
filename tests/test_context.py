from voice_operator.context import friendly_app_name, AppContext


def test_known_apps_map_to_friendly_names():
    assert friendly_app_name("slack.exe") == "Slack"
    assert friendly_app_name("Code.exe") == "VS Code"
    assert friendly_app_name("Cursor.exe") == "Cursor"
    assert friendly_app_name("OUTLOOK.EXE") == "Outlook"
    assert friendly_app_name("Discord.exe") == "Discord"
    assert friendly_app_name("chrome.exe") == "Chrome"


def test_unknown_app_falls_back_to_stripped_exe():
    assert friendly_app_name("some_random_tool.exe") == "some_random_tool"
    assert friendly_app_name("") == "Unknown"


def test_app_context_is_a_dataclass():
    ctx = AppContext(app_name="Slack", window_title="general")
    assert ctx.app_name == "Slack"
    assert ctx.window_title == "general"
