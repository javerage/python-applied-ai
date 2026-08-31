from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

import python_applied_ai
from python_applied_ai.config import Settings


def test_package_can_be_imported() -> None:
    assert python_applied_ai.__name__ == "python_applied_ai"


def test_main_stops_when_groq_api_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Do not construct the chatbot when GROQ_API_KEY is missing."""

    settings = Settings.model_construct(
        llm_model="openai/gpt-oss-20b",
        llm_max_tokens=256,
        groq_api_key=None,
    )

    get_settings_mock = MagicMock(return_value=settings)
    groq_constructor = MagicMock()
    chatbot_constructor = MagicMock()
    run_cli_mock = MagicMock()

    monkeypatch.setattr(
        python_applied_ai,
        "get_settings",
        get_settings_mock,
        raising=False,
    )
    monkeypatch.setattr(
        python_applied_ai,
        "Groq",
        groq_constructor,
        raising=False,
    )
    monkeypatch.setattr(
        python_applied_ai,
        "ChatBot",
        chatbot_constructor,
        raising=False,
    )
    monkeypatch.setattr(
        python_applied_ai,
        "run_cli",
        run_cli_mock,
        raising=False,
    )

    python_applied_ai.main()

    get_settings_mock.assert_called_once_with()
    groq_constructor.assert_not_called()
    chatbot_constructor.assert_not_called()
    run_cli_mock.assert_not_called()

    assert capsys.readouterr().out == ("Missing GROQ API KEY. Add it to .env and retry.\n")


def test_main_builds_chatbot_and_runs_cli_with_valid_api_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build the configured chatbot and delegate execution to run_cli."""

    settings = Settings.model_construct(
        llm_model="openai/gpt-oss-20b",
        llm_max_tokens=256,
        groq_api_key=SecretStr("test-api-key"),
    )

    fake_client = MagicMock()
    fake_bot = MagicMock()

    get_settings_mock = MagicMock(return_value=settings)
    groq_constructor = MagicMock(return_value=fake_client)
    chatbot_constructor = MagicMock(return_value=fake_bot)
    run_cli_mock = MagicMock()

    monkeypatch.setattr(
        python_applied_ai,
        "get_settings",
        get_settings_mock,
    )
    monkeypatch.setattr(
        python_applied_ai,
        "Groq",
        groq_constructor,
        raising=False,
    )
    monkeypatch.setattr(
        python_applied_ai,
        "ChatBot",
        chatbot_constructor,
        raising=False,
    )
    monkeypatch.setattr(
        python_applied_ai,
        "run_cli",
        run_cli_mock,
        raising=False,
    )

    python_applied_ai.main()

    get_settings_mock.assert_called_once_with()
    groq_constructor.assert_called_once_with(api_key="test-api-key")
    chatbot_constructor.assert_called_once_with(
        fake_client,
        settings,
        "You are a helpful Python and AI assistant.",
    )
    run_cli_mock.assert_called_once_with(fake_bot)

    assert capsys.readouterr().out == ""
