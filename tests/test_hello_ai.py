"""Offline tests for the AI call boundary."""

from collections.abc import Callable
from typing import cast
from unittest.mock import MagicMock, patch

import httpx
import pytest
from groq import (
    APIConnectionError,
    AuthenticationError,
    Groq,
    GroqError,
    NotFoundError,
    RateLimitError,
)
from pydantic import SecretStr

from python_applied_ai.config import Settings
from python_applied_ai.hello_ai import call_ai, main


def _fake_request() -> httpx.Request:
    """Create an in-memory HTTP request without network access."""

    return httpx.Request(
        "POST",
        "https://api.groq.com/v1/chat/completions",
    )


def _connection_error() -> APIConnectionError:
    """Create an offline Groq connection error."""

    return APIConnectionError(
        message="Connection failed",
        request=_fake_request(),
    )


def _auth_error() -> AuthenticationError:
    """Create an offline authentication error."""

    request = _fake_request()

    return AuthenticationError(
        "SENSITIVE_PROVIDER_DETAIL",
        response=httpx.Response(
            401,
            request=request,
        ),
        body=None,
    )


def _rate_limit_error() -> RateLimitError:
    """Create an offline rate-limit error."""

    request = _fake_request()

    return RateLimitError(
        "SENSITIVE_PROVIDER_DETAIL",
        response=httpx.Response(
            429,
            request=request,
        ),
        body=None,
    )


def _not_found_error() -> NotFoundError:
    """Create an offline resource-not-found error."""

    request = _fake_request()

    return NotFoundError(
        "SENSITIVE_PROVIDER_DETAIL",
        response=httpx.Response(
            404,
            request=request,
        ),
        body=None,
    )


def _test_settings(
    *,
    groq_api_key: SecretStr | None = None,
    llm_model: str = "openai/gpt-oss-20b",
    llm_max_tokens: int = 256,
) -> Settings:
    """Build trusted test settings without reading environment sources."""

    return Settings.model_construct(
        groq_api_key=groq_api_key,
        llm_model=llm_model,
        llm_max_tokens=llm_max_tokens,
    )


def test_call_ai_propagates_connection_error() -> None:
    """The domain function must let typed Groq errors propagate."""

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = _connection_error()
    fake_client = cast(Groq, mock_client)

    settings = _test_settings()

    with pytest.raises(APIConnectionError):
        call_ai(fake_client, "Hi", settings)


def test_main_handles_unexpected_groq_error_safely(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI boundary must hide raw provider error details."""

    settings = _test_settings(
        groq_api_key=SecretStr("test-key"),
    )
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = GroqError("SENSITIVE_PROVIDER_DETAIL")

    with (
        patch(
            "python_applied_ai.hello_ai.get_settings",
            return_value=settings,
        ),
        patch(
            "python_applied_ai.hello_ai.Groq",
            return_value=fake_client,
        ),
    ):
        main()

    captured = capsys.readouterr()

    assert "unexpected groq" in captured.out.lower()
    assert "SENSITIVE_PROVIDER_DETAIL" not in captured.out


@pytest.mark.parametrize(
    ("make_error", "expected_fragment"),
    [
        (_auth_error, "authentication failed"),
        (_rate_limit_error, "rate limit"),
        (_not_found_error, "model not found"),
        (_connection_error, "connection error"),
    ],
)
def test_main_handles_specific_groq_errors_safely(
    capsys: pytest.CaptureFixture[str],
    make_error: Callable[[], GroqError],
    expected_fragment: str,
) -> None:
    """Each known Groq error must produce a safe, specific message."""

    settings = _test_settings(
        groq_api_key=SecretStr("test-key"),
    )
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = make_error()

    with (
        patch(
            "python_applied_ai.hello_ai.get_settings",
            return_value=settings,
        ),
        patch(
            "python_applied_ai.hello_ai.Groq",
            return_value=fake_client,
        ),
    ):
        main()

    captured = capsys.readouterr()

    assert expected_fragment in captured.out.lower()
    assert "SENSITIVE_PROVIDER_DETAIL" not in captured.out
