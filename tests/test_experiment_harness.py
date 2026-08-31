"""Offline tests for the temperature experiment harness."""

import dataclasses
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

from python_applied_ai.config import Settings
from python_applied_ai.experiment_temperature import run_temperature_sweep


def _fake_response(
    content: str | None,
    fingerprint: str | None = "fp-abc",
    model: str = "openai/gpt-oss-20b",
) -> MagicMock:
    resp = MagicMock()
    resp.model = model
    resp.system_fingerprint = fingerprint
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 20
    resp.usage.total_tokens = 30
    resp.usage.completion_tokens_details.reasoning_tokens = 5
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    return resp


def _test_settings() -> Settings:
    return Settings.model_construct(
        llm_model="openai/gpt-oss-20b",
        llm_max_tokens=256,
        llm_input_rate_per_million=None,
        llm_output_rate_per_million=None,
    )


def test_sweep_records_rows_without_network() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_response("a"),
        _fake_response("b"),
        _fake_response("c"),
    ]
    settings = _test_settings()

    rows = run_temperature_sweep(fake_client, settings, "q", [0.0, 0.7, 1.2])

    assert len(rows) == 3
    assert rows[0].temperature == 0.0
    assert rows[1].temperature == 0.7
    assert rows[2].temperature == 1.2


def test_sweep_no_id_in_rows() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_response("a"),
    ]
    settings = _test_settings()

    rows = run_temperature_sweep(fake_client, settings, "q", [0.0])

    row_dict = dataclasses.asdict(rows[0])
    assert "id" not in row_dict
    assert "_id" not in row_dict


def test_sweep_seed_none() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [_fake_response("a")]
    settings = _test_settings()

    rows = run_temperature_sweep(fake_client, settings, "q", [0.0], seed=None)

    assert rows[0].seed is None
    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["seed"] is None


def test_sweep_seed_present() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [_fake_response("a")]
    settings = _test_settings()

    rows = run_temperature_sweep(fake_client, settings, "q", [0.0], seed=42)

    assert rows[0].seed == 42
    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["seed"] == 42


def test_sweep_fingerprint_none() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [_fake_response("a", fingerprint=None)]
    settings = _test_settings()

    rows = run_temperature_sweep(fake_client, settings, "q", [0.0])

    assert rows[0].system_fingerprint is None


def test_sweep_output_none_to_empty_string() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [_fake_response(None)]
    settings = _test_settings()

    rows = run_temperature_sweep(fake_client, settings, "q", [0.0])

    assert rows[0].output == ""


def test_sweep_order() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_response("a"),
        _fake_response("b"),
        _fake_response("c"),
    ]
    settings = _test_settings()

    rows = run_temperature_sweep(fake_client, settings, "q", [0.0, 0.7, 1.2])

    assert rows[0].temperature == 0.0
    assert rows[1].temperature == 0.7
    assert rows[2].temperature == 1.2
    assert rows[0].output == "a"
    assert rows[1].output == "b"
    assert rows[2].output == "c"


def test_sweep_one_call_per_temperature() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_response("a"),
        _fake_response("b"),
    ]
    settings = _test_settings()

    run_temperature_sweep(fake_client, settings, "q", [0.0, 1.2])

    assert fake_client.chat.completions.create.call_count == 2


def test_sweep_validates_all_temperatures_before_any_call() -> None:
    fake_client = MagicMock()
    settings = _test_settings()

    with pytest.raises(ValueError):
        run_temperature_sweep(fake_client, settings, "q", [-0.1, 0.7, 1.2])

    fake_client.chat.completions.create.assert_not_called()


def test_sweep_model_field() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_response("a", model="openai/gpt-oss-20b")
    ]
    settings = _test_settings()

    rows = run_temperature_sweep(fake_client, settings, "q", [0.0])

    assert rows[0].model == "openai/gpt-oss-20b"


def test_sweep_uses_frozen_dataclass() -> None:
    from python_applied_ai.experiment_temperature import TemperatureRow

    row = TemperatureRow(
        temperature=0.0,
        seed=None,
        model="openai/gpt-oss-20b",
        system_fingerprint=None,
        output="hello",
    )

    with pytest.raises(FrozenInstanceError):
        row.__setattr__("temperature", 1.0)

    assert hasattr(TemperatureRow, "__dataclass_fields__")
    assert TemperatureRow.__dataclass_fields__["temperature"].init is True


def test_sweep_fingerprint_field_present() -> None:
    from python_applied_ai.experiment_temperature import TemperatureRow

    fields = TemperatureRow.__dataclass_fields__
    assert "system_fingerprint" in fields
    assert fields["system_fingerprint"].init is True
