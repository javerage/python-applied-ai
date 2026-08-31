"""Offline tests for validate_temperature."""

import math

import pytest

from python_applied_ai.sampling import validate_temperature


def test_rejects_below_zero() -> None:
    with pytest.raises(ValueError):
        validate_temperature(-0.1)


def test_min_zero_ok() -> None:
    assert validate_temperature(0.0) == 0.0


def test_default_0_7_ok() -> None:
    assert validate_temperature(0.7) == 0.7


def test_1_2_ok() -> None:
    assert validate_temperature(1.2) == 1.2


def test_max_two_ok() -> None:
    assert validate_temperature(2.0) == 2.0


def test_rejects_above_two() -> None:
    with pytest.raises(ValueError):
        validate_temperature(2.1)


def test_rejects_nan() -> None:
    with pytest.raises(ValueError):
        validate_temperature(math.nan)


def test_rejects_positive_inf() -> None:
    with pytest.raises(ValueError):
        validate_temperature(math.inf)


def test_rejects_negative_inf() -> None:
    with pytest.raises(ValueError):
        validate_temperature(-math.inf)
