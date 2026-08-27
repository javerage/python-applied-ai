"""Make the first API call through the Groq LLM API."""

from decimal import Decimal

from groq import (
    APIConnectionError,
    AuthenticationError,
    Groq,
    GroqError,
    NotFoundError,
    RateLimitError,
)
from groq.types.chat import ChatCompletion
from groq.types.completion_usage import CompletionUsage

from python_applied_ai.config import Settings, get_settings
from python_applied_ai.cost import estimate_cost_usd


def format_usd(cost: Decimal) -> str:
    """Format a Decimal cost without losing precision."""

    formatted = format(cost, "f")

    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")

    return formatted or "0"


def report_theoretical_cost(
    usage: CompletionUsage,
    settings: Settings,
) -> None:
    """Print a theoretical list-price estimate using configured rates."""

    input_rate = settings.llm_input_rate_per_million
    output_rate = settings.llm_output_rate_per_million

    print("\nTHEORETICAL LIST-PRICE ESTIMATE — NOT BILLED")

    if input_rate is None or output_rate is None:
        print("Skipped: token rates are not configured.")
        return

    cost = estimate_cost_usd(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        input_rate_per_million=input_rate,
        output_rate_per_million=output_rate,
    )

    print(f"Estimated cost: USD {format_usd(cost)}")


def report_usage(
    response: ChatCompletion,
    settings: Settings,
) -> None:
    """Report token usage statistics and theoretical cost."""
    print(f"\nResponse ID: {response.id}")
    print(f"Model used: {response.model}")

    usage = response.usage
    if usage is None:
        print("Token usage is not available for this response")
        return
    print("\nToken Usage:")
    print(f"Input tokens: {usage.prompt_tokens}")
    print(f"Output tokens: {usage.completion_tokens}")
    print(f"Total tokens: {usage.total_tokens}")

    details = usage.completion_tokens_details
    if details is not None:
        print(f"Reasoning tokens: {details.reasoning_tokens}")

    report_theoretical_cost(usage, settings)


def call_ai(
    client: Groq,
    question: str,
    settings: Settings,
) -> ChatCompletion:
    """Call Groq and return the complete chat response."""

    return client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": question}],
        max_tokens=settings.llm_max_tokens,
        temperature=0.7,
        top_p=0.9,
    )


def main() -> None:
    """Print a greeting from the LLM."""
    settings = get_settings()

    if not settings.groq_api_key or not settings.groq_api_key.get_secret_value():
        print("Missing GROQ API KEY. Add it to .env and retry.")
        return

    client = Groq(api_key=settings.groq_api_key.get_secret_value())

    try:
        response = call_ai(
            client,
            "Say hello in three languages: Spanish, English, and French.",
            settings,
        )
    except AuthenticationError:
        print("Authentication failed: GROQ_API_KEY is invalid or revoked.")
        return
    except RateLimitError:
        print("Rate limit reached. Wait and retry later; do not loop.")
        return
    except NotFoundError:
        print(f"Model not found: {settings.llm_model}. Check LLM_MODEL in .env.")
        return
    except APIConnectionError:
        print("Connection error: check your network and retry.")
        return
    except GroqError:
        print("Unexpected Groq error. Try again later or check the Groq status page.")
        return

    content = response.choices[0].message.content
    print(content if content is not None else "The model returned an empty response.")
    report_usage(response, settings)


if __name__ == "__main__":
    main()
