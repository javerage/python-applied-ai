"""Offline tests for the CLI chatbot conversation history."""

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

from python_applied_ai.chatbot_cli import ChatBot
from python_applied_ai.config import Settings

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

    assert reply == "Hello"
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

    assert reply == "Second reply"

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

    assert reply == ""
    assert len(chatbot.history) == 3

    assistant_message = cast(
        ChatCompletionAssistantMessageParam,
        chatbot.history[2],
    )

    assert assistant_message["role"] == "assistant"
    assert assistant_message["content"] == ""
