"""Offline tests for call_ai temperature forwarding."""

from unittest.mock import MagicMock

import pytest

from python_applied_ai.config import Settings
from python_applied_ai.hello_ai import call_ai


def _test_settings() -> Settings:
    """Build trusted test settings without reading environment sources."""
    return Settings.model_construct(
        llm_model="openai/gpt-oss-20b",
        llm_max_tokens=256,
    )


def test_call_ai_forwards_temperature_and_seed() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock()
    settings = _test_settings()

    call_ai(fake_client, "hi", settings, temperature=1.2, seed=42)

    fake_client.chat.completions.create.assert_called_once()
    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["temperature"] == 1.2
    assert kwargs["seed"] == 42


def test_call_ai_default_temperature() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock()
    settings = _test_settings()

    call_ai(fake_client, "hi", settings)

    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["temperature"] == 0.7
    assert kwargs["seed"] is None


def test_call_ai_invalid_temperature_does_not_call_client() -> None:
    fake_client = MagicMock()
    settings = _test_settings()

    with pytest.raises(ValueError):
        call_ai(fake_client, "hi", settings, temperature=-1.0)

    fake_client.chat.completions.create.assert_not_called()


def test_call_ai_backward_compatible() -> None:
    """Existing three-argument call still works without temperature."""
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock()
    settings = _test_settings()

    result = call_ai(fake_client, "hi", settings)

    assert result is not None
    fake_client.chat.completions.create.assert_called_once()
