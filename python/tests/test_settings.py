import pytest

from config.settings import Settings


def test_settings_allow_disabled_notion():
    settings = Settings()
    settings.validate()

    assert settings.notion_enabled is False


def test_settings_require_complete_notion_credentials():
    settings = Settings(notion_token="token")

    with pytest.raises(ValueError, match="함께"):
        settings.validate()
