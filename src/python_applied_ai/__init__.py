from groq import Groq

from python_applied_ai.chatbot_cli import ChatBot, run_cli
from python_applied_ai.config import get_settings

SYSTEM_PROMPT = "You are a helpful Python and AI assistant."


def main() -> None:
    """Start the configured CLI chatbot."""

    settings = get_settings()
    api_key = settings.groq_api_key

    if not api_key:
        print("Missing GROQ API KEY. Add it to .env and retry.")
        return

    api_key_value = api_key.get_secret_value()

    if not api_key_value:
        print("Missing GROQ API KEY. Add it to .env and retry.")
        return

    client = Groq(api_key=api_key_value)
    bot = ChatBot(
        client,
        settings,
        SYSTEM_PROMPT,
    )

    run_cli(bot)
