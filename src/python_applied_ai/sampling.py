"""Provider-neutral temperature validation."""

from __future__ import annotations

import math

MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0


def validate_temperature(value: float) -> float:
    """Return value if within Groq's documented 0.0-2.0 range.

    Raises ValueError for NaN, infinite, or out-of-range values.
    Pure, provider-neutral guard.
    """
    if math.isnan(value) or math.isinf(value):
        raise ValueError(
            f"temperature must be a finite number in "
            f"[{MIN_TEMPERATURE}, {MAX_TEMPERATURE}], got {value}"
        )
    if value < MIN_TEMPERATURE or value > MAX_TEMPERATURE:
        raise ValueError(
            f"temperature must be in [{MIN_TEMPERATURE}, {MAX_TEMPERATURE}], got {value}"
        )
    return value
