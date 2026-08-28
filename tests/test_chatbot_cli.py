"""Offline tests for the CLI chatbot conversation history."""

from decimal import Decimal
from typing import cast
from unittest.mock import MagicMock

import httpx
import pytest
from groq import APIConnectionError, Groq
from groq.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from groq.types.completion_usage import CompletionUsage

from python_applied_ai.chatbot_cli import ChatBot
from python_applied_ai.config import Settings
from python_applied_ai.cost import estimate_cost_usd

SYSTEM_PROMPT = "You are a helpful Python and AI assistant."


def _test_settings() -> Settings:
    """Build trusted settings without reading environment sources."""

    return Settings.model_construct(
        llm_model="openai/gpt-oss-20b",
        llm_max_tokens=256,
    )


def _fake_completion(content: str | None) -> ChatCompletion:
    """Build an in-memory completion response."""

    response = MagicMock()
    response.choices[0].message.content = content
    response.usage = None

    return cast(ChatCompletion, response)


def _fake_request() -> httpx.Request:
    """Create an in-memory request without network access."""

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


def test_initial_history_has_system_message() -> None:
    """A new chatbot starts with exactly one system message."""

    settings = _test_settings()
    fake_client = MagicMock()

    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )

    assert len(chatbot.history) == 1

    system_message = cast(
        ChatCompletionSystemMessageParam,
        chatbot.history[0],
    )

    assert system_message["role"] == "system"
    assert system_message["content"] == SYSTEM_PROMPT
    fake_client.chat.completions.create.assert_not_called()


def test_first_chat_round_returns_reply_and_commits_history() -> None:
    """A successful chat round stores user and assistant messages."""

    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_completion("Hello")

    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )

    reply = chatbot.chat("Hello")

    assert reply.text == "Hello"
    fake_client.chat.completions.create.assert_called_once()

    assert len(chatbot.history) == 3

    user_message = cast(
        ChatCompletionUserMessageParam,
        chatbot.history[1],
    )
    assistant_message = cast(
        ChatCompletionAssistantMessageParam,
        chatbot.history[2],
    )

    assert user_message["role"] == "user"
    assert user_message["content"] == "Hello"
    assert assistant_message["role"] == "assistant"
    assert assistant_message["content"] == "Hello"


def test_second_chat_round_sends_prior_context() -> None:
    """The second request includes the previous user and assistant messages."""

    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_completion("First reply"),
        _fake_completion("Second reply"),
    ]

    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )

    chatbot.chat("First question")
    reply = chatbot.chat("Second question")

    assert reply.text == "Second reply"

    second_call = fake_client.chat.completions.create.call_args_list[1]
    messages = second_call.kwargs["messages"]

    assert messages == [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": "First question",
        },
        {
            "role": "assistant",
            "content": "First reply",
        },
        {
            "role": "user",
            "content": "Second question",
        },
    ]


def test_api_failure_leaves_history_unchanged() -> None:
    """A failed request must not leave an orphan user message in history."""

    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = _connection_error()

    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )

    with pytest.raises(APIConnectionError):
        chatbot.chat("This request fails")

    assert len(chatbot.history) == 1

    system_message = cast(
        ChatCompletionSystemMessageParam,
        chatbot.history[0],
    )

    assert system_message["role"] == "system"
    assert system_message["content"] == SYSTEM_PROMPT


def test_empty_response_content_returns_and_stores_empty_string() -> None:
    """An empty provider response is stored consistently as an empty string."""

    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_completion(None)

    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )

    reply = chatbot.chat("Hello")

    assert reply.text == ""
    assert len(chatbot.history) == 3

    assistant_message = cast(
        ChatCompletionAssistantMessageParam,
        chatbot.history[2],
    )

    assert assistant_message["role"] == "assistant"
    assert assistant_message["content"] == ""


def test_chat_returns_text_and_provider_usage() -> None:
    """A successful response exposes its text and provider usage."""

    usage = CompletionUsage(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    response = MagicMock()
    response.choices[0].message.content = "Hello"
    response.usage = usage

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = cast(
        ChatCompletion,
        response,
    )

    chatbot = ChatBot(
        cast(Groq, fake_client),
        _test_settings(),
        SYSTEM_PROMPT,
    )

    result = chatbot.chat("Hello")

    assert result.text == "Hello"
    assert result.usage == usage


def test_fresh_chatbot_reports_zeroed_session_stats() -> None:
    """A new chatbot reports zero usage and unknown theoretical cost."""

    chatbot = ChatBot(
        cast(Groq, MagicMock()),
        _test_settings(),
        SYSTEM_PROMPT,
    )

    stats = chatbot.stats()

    assert stats.turn_count == 0
    assert stats.prompt_tokens == 0
    assert stats.completion_tokens == 0
    assert stats.total_tokens == 0
    assert stats.theoretical_cost_usd is None


def test_successful_turn_accumulates_session_stats_without_cost() -> None:
    """One successful turn drives counts and tokens while cost stays unknown."""

    usage = CompletionUsage(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    response = MagicMock()
    response.choices[0].message.content = "Hello"
    response.usage = usage

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = cast(
        ChatCompletion,
        response,
    )

    chatbot = ChatBot(
        cast(Groq, fake_client),
        _test_settings(),
        SYSTEM_PROMPT,
    )

    chatbot.chat("Hello")

    stats = chatbot.stats()

    assert stats.turn_count == 1
    assert stats.prompt_tokens == 10
    assert stats.completion_tokens == 5
    assert stats.total_tokens == 15
    assert stats.theoretical_cost_usd is None


def test_successful_turn_accumulates_exact_theoretical_cost() -> None:
    """One successful turn with configured rates yields an exact Decimal cost."""

    usage = CompletionUsage(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    response = MagicMock()
    response.choices[0].message.content = "Hello"
    response.usage = usage

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = cast(
        ChatCompletion,
        response,
    )

    input_rate = Decimal("1.0")
    output_rate = Decimal("2.0")
    settings = Settings.model_construct(
        llm_model="openai/gpt-oss-20b",
        llm_max_tokens=256,
        llm_input_rate_per_million=input_rate,
        llm_output_rate_per_million=output_rate,
    )

    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )

    chatbot.chat("Hello")

    expected = estimate_cost_usd(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        input_rate_per_million=input_rate,
        output_rate_per_million=output_rate,
    )

    assert chatbot.stats().theoretical_cost_usd == expected
