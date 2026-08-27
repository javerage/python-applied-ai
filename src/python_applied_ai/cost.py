"""Provider-neutral token cost estimation"""

from decimal import Decimal

TOKENS_PER_MILLION = Decimal("1_000_000")


def estimate_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    input_rate_per_million: Decimal,
    output_rate_per_million: Decimal,
) -> Decimal:
    """Estimate list-price cost using externally supplied per-million rates."""
    if prompt_tokens < 0 or completion_tokens < 0:
        raise ValueError("Token counts must be non-negative")

    if input_rate_per_million < 0 or output_rate_per_million < 0:
        raise ValueError("Token rates must be non-negative")

    input_cost = (Decimal(prompt_tokens) * input_rate_per_million) / TOKENS_PER_MILLION
    output_cost = (Decimal(completion_tokens) * output_rate_per_million) / TOKENS_PER_MILLION
    return input_cost + output_cost
