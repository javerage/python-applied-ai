"""Tests for typed application settings."""

import math

import pytest
from pydantic import ValidationError

from python_applied_ai.config import Settings


def test_temperature_defaults_to_balanced_value() -> None:
    settings = Settings.model_validate({})

    assert settings.llm_temperature == 0.7


def test_temperature_accepts_configured_value() -> None:
    settings = Settings.model_validate({"llm_temperature": 1.2})

    assert settings.llm_temperature == 1.2


@pytest.mark.parametrize(
    "value",
    [-0.1, 2.1, math.nan, math.inf, -math.inf],
)
def test_temperature_rejects_invalid_values(value: float) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"llm_temperature": value})
