"""CLI chatbot domain with in-memory conversation history."""

from dataclasses import dataclass
from decimal import Decimal

from groq import Groq
from groq.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from groq.types.completion_usage import CompletionUsage

from python_applied_ai.config import Settings
from python_applied_ai.cost import estimate_cost_usd


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """Represent one successful chatbot response."""

    text: str
    usage: CompletionUsage | None


@dataclass(frozen=True, slots=True)
class SessionStats:
    """Represent an immutable snapshot of chatbot session totals."""

    turn_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    theoretical_cost_usd: Decimal | None


def format_stats(stats: SessionStats) -> str:
    """Render an immutable session snapshot as a deterministic CLI summary."""

    cost = stats.theoretical_cost_usd
    cost_text = "unavailable" if cost is None else str(cost)

    return (
        "Session statistics:\n"
        f"Turns: {stats.turn_count}\n"
        f"Prompt tokens: {stats.prompt_tokens}\n"
        f"Completion tokens: {stats.completion_tokens}\n"
        f"Total tokens: {stats.total_tokens}\n"
        f"Theoretical cost (USD, not billed): {cost_text}"
    )


class ChatBot:
    """Maintain one CLI chatbot session in memory."""

    def __init__(
        self,
        client: Groq,
        settings: Settings,
        system_prompt: str,
    ) -> None:
        self.client = client
        self.settings = settings
        self._system_prompt = system_prompt
        self.history: list[ChatCompletionMessageParam] = [self._build_system_message()]
        self._stats = self._build_initial_stats()

    def _build_system_message(self) -> ChatCompletionSystemMessageParam:
        """Build the opening system message."""

        return ChatCompletionSystemMessageParam(
            role="system",
            content=self._system_prompt,
        )

    def _build_initial_stats(self) -> SessionStats:
        """Build a zeroed session snapshot with rate-aware cost."""

        both_rates_configured = (
            self.settings.llm_input_rate_per_million is not None
            and self.settings.llm_output_rate_per_million is not None
        )
        initial_cost = Decimal("0") if both_rates_configured else None

        return SessionStats(
            turn_count=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            theoretical_cost_usd=initial_cost,
        )

    def reset_session(self) -> None:
        """Restore the chatbot to its initial session state."""

        system_message = self._build_system_message()
        initial_stats = self._build_initial_stats()

        self.history[:] = [system_message]
        self._stats = initial_stats

    def chat(self, user_message: str) -> ChatTurn:
        """Send one message and commit a successful conversation round."""

        user_entry = ChatCompletionUserMessageParam(
            role="user",
            content=user_message,
        )
        pending_history: list[ChatCompletionMessageParam] = [
            *self.history,
            user_entry,
        ]

        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=pending_history,
            max_tokens=self.settings.llm_max_tokens,
            temperature=0.7,
            top_p=0.9,
        )

        content = response.choices[0].message.content or ""
        assistant_entry = ChatCompletionAssistantMessageParam(
            role="assistant",
            content=content,
        )

        usage = response.usage

        if usage is None:
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
        else:
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

        input_rate = self.settings.llm_input_rate_per_million
        output_rate = self.settings.llm_output_rate_per_million

        if input_rate is None or output_rate is None:
            next_cost = None
        elif usage is None:
            next_cost = self._stats.theoretical_cost_usd
        else:
            turn_cost = estimate_cost_usd(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                input_rate_per_million=input_rate,
                output_rate_per_million=output_rate,
            )
            prior_cost = self._stats.theoretical_cost_usd
            if prior_cost is None:
                prior_cost = Decimal("0")

            next_cost = prior_cost + turn_cost

        next_stats = SessionStats(
            turn_count=self._stats.turn_count + 1,
            prompt_tokens=self._stats.prompt_tokens + prompt_tokens,
            completion_tokens=self._stats.completion_tokens + completion_tokens,
            total_tokens=self._stats.total_tokens + total_tokens,
            theoretical_cost_usd=next_cost,
        )

        self.history.append(user_entry)
        self.history.append(assistant_entry)
        self._stats = next_stats

        return ChatTurn(
            text=content,
            usage=usage,
        )

    def stats(self) -> SessionStats:
        """Return the current session statistics."""

        return self._stats
