"""Offline tests for the CLI chatbot conversation history."""

from decimal import Decimal
from typing import cast
from unittest.mock import MagicMock

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
from groq.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from groq.types.completion_usage import CompletionUsage

from python_applied_ai import chatbot_cli
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
    """Create an offline rate limit error."""

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
    """Create an offline model-not-found error."""

    request = _fake_request()

    return NotFoundError(
        "SENSITIVE_PROVIDER_DETAIL",
        response=httpx.Response(
            404,
            request=request,
        ),
        body=None,
    )


def _groq_error() -> GroqError:
    """Create an offline generic Groq error."""

    return GroqError("SENSITIVE_PROVIDER_DETAIL")


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
    """A failed request must not mutate history or session stats."""

    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = _connection_error()

    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )

    stats_before = chatbot.stats()

    with pytest.raises(APIConnectionError):
        chatbot.chat("This request fails")

    assert len(chatbot.history) == 1

    system_message = cast(
        ChatCompletionSystemMessageParam,
        chatbot.history[0],
    )

    assert system_message["role"] == "system"
    assert system_message["content"] == SYSTEM_PROMPT
    assert chatbot.stats() == stats_before


def test_empty_response_content_returns_and_stores_empty_string() -> None:
    """An empty provider response is one successful turn with zero known usage."""

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

    stats = chatbot.stats()

    assert stats.turn_count == 1
    assert stats.prompt_tokens == 0
    assert stats.completion_tokens == 0
    assert stats.total_tokens == 0
    assert stats.theoretical_cost_usd is None


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


def test_reset_session_zeroes_stats_and_preserves_system_with_rates() -> None:
    """Reset restores zeroed stats and preserves only the system message."""

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

    settings = Settings.model_construct(
        llm_model="openai/gpt-oss-20b",
        llm_max_tokens=256,
        llm_input_rate_per_million=Decimal("1.0"),
        llm_output_rate_per_million=Decimal("2.0"),
    )
    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )
    chatbot.chat("Hello")

    chatbot.reset_session()

    stats = chatbot.stats()

    assert stats.turn_count == 0
    assert stats.prompt_tokens == 0
    assert stats.completion_tokens == 0
    assert stats.total_tokens == 0
    assert stats.theoretical_cost_usd == Decimal("0")

    assert len(chatbot.history) == 1

    system_message = cast(
        ChatCompletionSystemMessageParam,
        chatbot.history[0],
    )
    assert system_message["role"] == "system"
    assert system_message["content"] == SYSTEM_PROMPT


def test_reset_session_zeroes_stats_and_preserves_system_without_rates() -> None:
    """Reset without rates restores zeroed stats with unknown cost."""

    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_completion("Hello")

    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )
    chatbot.chat("Hello")

    assert chatbot.stats().turn_count == 1
    assert len(chatbot.history) == 3

    chatbot.reset_session()

    stats = chatbot.stats()

    assert stats.turn_count == 0
    assert stats.prompt_tokens == 0
    assert stats.completion_tokens == 0
    assert stats.total_tokens == 0
    assert stats.theoretical_cost_usd is None

    assert len(chatbot.history) == 1

    system_message = cast(
        ChatCompletionSystemMessageParam,
        chatbot.history[0],
    )
    assert system_message["role"] == "system"
    assert system_message["content"] == SYSTEM_PROMPT


def test_two_successful_turns_accumulate_exact_token_totals_and_cost() -> None:
    """Two successful turns sum token totals and Decimal cost."""

    usage_first = CompletionUsage(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    usage_second = CompletionUsage(
        prompt_tokens=20,
        completion_tokens=8,
        total_tokens=28,
    )

    first_response = MagicMock()
    first_response.choices[0].message.content = "First reply"
    first_response.usage = usage_first

    second_response = MagicMock()
    second_response.choices[0].message.content = "Second reply"
    second_response.usage = usage_second

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        cast(ChatCompletion, first_response),
        cast(ChatCompletion, second_response),
    ]

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

    chatbot.chat("First question")
    chatbot.chat("Second question")

    expected_cost = estimate_cost_usd(
        prompt_tokens=usage_first.prompt_tokens,
        completion_tokens=usage_first.completion_tokens,
        input_rate_per_million=input_rate,
        output_rate_per_million=output_rate,
    ) + estimate_cost_usd(
        prompt_tokens=usage_second.prompt_tokens,
        completion_tokens=usage_second.completion_tokens,
        input_rate_per_million=input_rate,
        output_rate_per_million=output_rate,
    )

    stats = chatbot.stats()

    assert stats.turn_count == 2
    assert stats.prompt_tokens == 30
    assert stats.completion_tokens == 13
    assert stats.total_tokens == 43
    assert stats.theoretical_cost_usd == expected_cost


def test_failed_second_turn_preserves_accumulated_session_state() -> None:
    """A failed second turn preserves the first successful turn state."""

    usage_first = CompletionUsage(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    first_response = MagicMock()
    first_response.choices[0].message.content = "First reply"
    first_response.usage = usage_first

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        cast(ChatCompletion, first_response),
        _connection_error(),
    ]

    settings = Settings.model_construct(
        llm_model="openai/gpt-oss-20b",
        llm_max_tokens=256,
        llm_input_rate_per_million=Decimal("1.0"),
        llm_output_rate_per_million=Decimal("2.0"),
    )
    chatbot = ChatBot(
        cast(Groq, fake_client),
        settings,
        SYSTEM_PROMPT,
    )

    chatbot.chat("First question")

    stats_after_first = chatbot.stats()
    history_after_first = list(chatbot.history)

    with pytest.raises(APIConnectionError):
        chatbot.chat("This second request fails")

    assert chatbot.stats() == stats_after_first
    assert chatbot.history == history_after_first


def test_format_stats_renders_session_summary() -> None:
    """Format session statistics as a deterministic CLI summary."""

    stats = chatbot_cli.SessionStats(
        turn_count=2,
        prompt_tokens=30,
        completion_tokens=13,
        total_tokens=43,
        theoretical_cost_usd=Decimal("0.00003"),
    )

    rendered = chatbot_cli.format_stats(stats)

    assert rendered == (
        "Session statistics:\n"
        "Turns: 2\n"
        "Prompt tokens: 30\n"
        "Completion tokens: 13\n"
        "Total tokens: 43\n"
        "Theoretical cost (USD, not billed): 0.00003"
    )


def test_format_stats_marks_unavailable_cost_when_none() -> None:
    """Render unavailable when theoretical cost was not computed."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )

    rendered = chatbot_cli.format_stats(stats)

    assert rendered == (
        "Session statistics:\n"
        "Turns: 0\n"
        "Prompt tokens: 0\n"
        "Completion tokens: 0\n"
        "Total tokens: 0\n"
        "Theoretical cost (USD, not billed): unavailable"
    )


@pytest.mark.parametrize(
    "user_command",
    ["exit", "QUIT", "  salir  ", "Bye"],
)
def test_run_cli_exits_after_single_exit_command(user_command: str) -> None:
    """Exit after one command without calling the model."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )
    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(return_value=user_command)
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    input_mock.assert_called_once_with("You: ")
    fake_bot.chat.assert_not_called()
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [chatbot_cli.format_stats(stats)]


def test_run_cli_ignores_blank_input_before_exit() -> None:
    """Ignore whitespace-only input and continue until exit."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )
    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=["   ", "exit"])
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    assert input_mock.call_count == 2
    fake_bot.chat.assert_not_called()
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [chatbot_cli.format_stats(stats)]


def test_run_cli_prints_stats_on_stats_command() -> None:
    """Print session stats on /stats without calling chat or reset."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )
    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=["/stats", "exit"])
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    assert input_mock.call_count == 2
    fake_bot.chat.assert_not_called()
    fake_bot.reset_session.assert_not_called()
    assert fake_bot.stats.call_count == 2

    assert outputs == [
        chatbot_cli.format_stats(stats),
        chatbot_cli.format_stats(stats),
    ]


def test_run_cli_resets_session_before_exit() -> None:
    """Reset the session and print a fixed confirmation."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )
    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=["/reset", "exit"])
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    assert input_mock.call_count == 2
    fake_bot.reset_session.assert_called_once_with()
    fake_bot.chat.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [
        "Conversation reset.",
        chatbot_cli.format_stats(stats),
    ]


def test_run_cli_executes_normal_turn() -> None:
    """A normal message calls chat and prints the reply text."""

    usage = CompletionUsage(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    turn = chatbot_cli.ChatTurn(
        text="Hello",
        usage=usage,
    )

    stats = chatbot_cli.SessionStats(
        turn_count=1,
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        theoretical_cost_usd=None,
    )

    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.chat.return_value = turn
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=["Hello", "exit"])
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    assert input_mock.call_count == 2
    fake_bot.chat.assert_called_once_with("Hello")
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [
        "Hello",
        chatbot_cli.format_stats(stats),
    ]


def test_run_cli_eof_error_ends_session() -> None:
    """EOFError ends the session without calling chat or reset."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )

    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=EOFError)
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    input_mock.assert_called_once_with("You: ")
    fake_bot.chat.assert_not_called()
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [
        "Input closed. Ending session.",
        chatbot_cli.format_stats(stats),
    ]


def test_run_cli_authentication_error_continues_loop() -> None:
    """Handle AuthenticationError safely and continue until exit."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )

    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.chat.side_effect = _auth_error()
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=["Hello", "exit"])
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    assert input_mock.call_count == 2
    fake_bot.chat.assert_called_once_with("Hello")
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [
        "Authentication failed. Check the configured API key.",
        chatbot_cli.format_stats(stats),
    ]


def test_run_cli_rate_limit_error_continues_loop() -> None:
    """Handle RateLimitError safely without retrying the provider."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )

    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.chat.side_effect = _rate_limit_error()
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=["Hello", "exit"])
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    assert input_mock.call_count == 2
    fake_bot.chat.assert_called_once_with("Hello")
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [
        "Rate limit reached. Try again later; do not loop.",
        chatbot_cli.format_stats(stats),
    ]


def test_run_cli_not_found_error_continues_loop() -> None:
    """Handle NotFoundError safely and continue until exit."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )

    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.chat.side_effect = _not_found_error()
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=["Hello", "exit"])
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    assert input_mock.call_count == 2
    fake_bot.chat.assert_called_once_with("Hello")
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [
        "Configured model was not found.",
        chatbot_cli.format_stats(stats),
    ]


def test_run_cli_connection_error_continues_loop() -> None:
    """Handle APIConnectionError safely and continue until exit."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )

    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.chat.side_effect = _connection_error()
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=["Hello", "exit"])
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    assert input_mock.call_count == 2
    fake_bot.chat.assert_called_once_with("Hello")
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [
        "Connection error. Check the network and retry later.",
        chatbot_cli.format_stats(stats),
    ]


def test_run_cli_generic_groq_error_continues_loop() -> None:
    """Handle a generic GroqError safely and continue until exit."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )

    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.chat.side_effect = _groq_error()
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=["Hello", "exit"])
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    assert input_mock.call_count == 2
    fake_bot.chat.assert_called_once_with("Hello")
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [
        "Unexpected Groq error. Try again later or check the status page.",
        chatbot_cli.format_stats(stats),
    ]


def test_run_cli_keyboard_interrupt_ends_session() -> None:
    """KeyboardInterrupt ends the session and prints its final summary."""

    stats = chatbot_cli.SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=None,
    )

    fake_bot = MagicMock(spec=ChatBot)
    fake_bot.stats.return_value = stats

    input_mock = MagicMock(side_effect=KeyboardInterrupt)
    outputs: list[str] = []

    chatbot_cli.run_cli(
        cast(ChatBot, fake_bot),
        input_fn=input_mock,
        output_fn=outputs.append,
    )

    input_mock.assert_called_once_with("You: ")
    fake_bot.chat.assert_not_called()
    fake_bot.reset_session.assert_not_called()
    fake_bot.stats.assert_called_once_with()

    assert outputs == [
        "\nSession interrupted.",
        chatbot_cli.format_stats(stats),
    ]
