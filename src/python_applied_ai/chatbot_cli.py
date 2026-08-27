"""CLI chatbot domain with in-memory conversation history."""

from groq import Groq
from groq.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from python_applied_ai.config import Settings


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
        self.history: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content=system_prompt,
            )
        ]

    def chat(self, user_message: str) -> str:
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

        self.history.append(user_entry)
        self.history.append(assistant_entry)

        return content
