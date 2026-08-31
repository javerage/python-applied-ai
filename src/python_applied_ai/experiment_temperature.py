"""Temperature sweep harness for controlled experiments."""

from __future__ import annotations

from dataclasses import dataclass

from groq import Groq

from python_applied_ai.config import Settings
from python_applied_ai.hello_ai import call_ai
from python_applied_ai.sampling import validate_temperature


@dataclass(frozen=True, slots=True)
class TemperatureRow:
    """Immutable record of one temperature measurement."""

    temperature: float
    seed: int | None
    model: str
    system_fingerprint: str | None
    output: str


def run_temperature_sweep(
    client: Groq,
    settings: Settings,
    prompt: str,
    temperatures: list[float],
    seed: int | None = None,
) -> list[TemperatureRow]:
    """Iterate each value in `temperatures` as a distinct experiment config.

    One live sample per temperature. Validates all temperatures before any
    call so an invalid value never produces a partial run. No retries,
    sleeps, or hidden loops.
    """
    for temperature in temperatures:
        validate_temperature(temperature)

    rows: list[TemperatureRow] = []

    for temperature in temperatures:
        response = call_ai(
            client,
            prompt,
            settings,
            temperature=temperature,
            seed=seed,
        )
        content = (
            response.choices[0].message.content
            if response.choices and response.choices[0] and response.choices[0].message
            else None
        )
        rows.append(
            TemperatureRow(
                temperature=temperature,
                seed=seed,
                model=response.model,
                system_fingerprint=getattr(response, "system_fingerprint", None),
                output=content if content is not None else "",
            )
        )

    return rows
