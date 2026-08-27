"""Tests for provider-neutral token cost estimation."""

from decimal import Decimal

import pytest

from python_applied_ai.cost import estimate_cost_usd


def test_estimates_cost_with_decimal_rates() -> None:
    cost = estimate_cost_usd(
        prompt_tokens=40,
        completion_tokens=120,
        input_rate_per_million=Decimal("0.000100"),
        output_rate_per_million=Decimal("0.000300"),
    )

    assert cost == Decimal("4.0E-8")


def test_returns_zero_when_no_tokens_are_used() -> None:
    cost = estimate_cost_usd(
        prompt_tokens=0,
        completion_tokens=0,
        input_rate_per_million=Decimal("1.00"),
        output_rate_per_million=Decimal("2.00"),
    )

    assert cost == Decimal("0")


def test_preserves_decimal_precision() -> None:
    cost = estimate_cost_usd(
        prompt_tokens=1,
        completion_tokens=1,
        input_rate_per_million=Decimal("0.1"),
        output_rate_per_million=Decimal("0.2"),
    )

    assert cost == Decimal("0.0000003")


@pytest.mark.parametrize(
    (
        "prompt_tokens",
        "completion_tokens",
        "input_rate_per_million",
        "output_rate_per_million",
    ),
    [
        (-1, 0, Decimal("1"), Decimal("1")),
        (0, -1, Decimal("1"), Decimal("1")),
        (0, 0, Decimal("-1"), Decimal("1")),
        (0, 0, Decimal("1"), Decimal("-1")),
    ],
)
def test_rejects_negative_values(
    prompt_tokens: int,
    completion_tokens: int,
    input_rate_per_million: Decimal,
    output_rate_per_million: Decimal,
) -> None:
    with pytest.raises(ValueError):
        estimate_cost_usd(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            input_rate_per_million=input_rate_per_million,
            output_rate_per_million=output_rate_per_million,
        )
