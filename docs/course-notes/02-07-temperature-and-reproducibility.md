# Temperatura y reproducibilidad con Groq

> **Aviso de derechos y privacidad:** Esta guía es una adaptación original basada en conceptos de un curso de pago, no una reproducción de su transcripción. No incluye texto literal de lecciones, identificadores de cuentas/proyectos o de medios (p. ej. Wistia), URLs de medios, metadatos de respuesta, marcas de tiempo, identificadores de respuesta, claves de API, valores de `.env`, tarifas privadas ni rutas personales. Las referencias apuntan únicamente a documentación oficial de Groq.

## Estado

**Planned** — lección de la sección 2. Prerrequisitos: [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) (costo) ya completado y sincronizado, y [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md) (manejo de errores) **debe implementarse primero**. El código aquí descrito es un **plan**: no está implementado, no se ha ejecutado `ruff`/`mypy`/`pytest` sobre él, y no debe marcarse como terminado. Los hechos de Groq citados se verificaron contra la documentación oficial (Context7) y el SDK instalado.

## Objetivo de aprendizaje

Comprender qué controla realmente `temperature` en Groq, por qué `temperature=0` no garantiza salida idéntica, cómo aproximar la reproducibilidad con `seed` y `system_fingerprint`, y cómo ejecutar un experimento controlado y consciente de cuota sobre `openai/gpt-oss-20b` sin reclamar prueba estadística ni realizar llamadas repetidas.

## Ruta rápida

1. (Hecho) [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) completo — medición de tokens y costo teórico.
2. (Planned) Implementar [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md) (define `call_ai`) antes de esta lección.
3. (Planned) Añadir `validate_temperature` puro en `src/python_applied_ai/sampling.py`.
4. (Planned) Extender `call_ai` con `temperature: float = 0.7` y un harness de experimento separado.
5. (Planned) Verificar con `ruff format --check .`, `ruff check .`, `mypy src` y `pytest` (pruebas 100% offline).

## Concepto del instructor vs. mapeo riguroso a Groq

La lección original sobre temperatura enseña la intuición de "más bajo = más determinista, más alto = más creativo". Esta guía conserva esa intuición como **punto de partida** y la vincula a los hechos documentados de Groq; no reproduce el material del curso.

| Concepto (intuición del curso) | Mapeo riguroso en Groq |
| --- | --- |
| "Temperatura baja = determinista" | `temperature=0` solo **reduce** la aleatoriedad de muestreo; **no** garantiza salida idéntica. Para aproximar reproducibilidad use `seed` (best-effort). |
| "Temperatura alta = creativa" | Aumenta la diversidad del muestreo; **no** garantiza creatividad ni corrección factual. |
| "Bandas determinista / equilibrada / creativa / caótica" | Etiquetas **heurísticas**, no tiers oficiales de Groq. El rango documentado es **0–2**. |
| "Ajustar temperature y top_p a la vez" | Evítelo: son controles de muestreo distintos. Ajuste **uno a la vez** (guía oficial de muestreo). |
| "Temperatura controla la calidad" | No: la calidad depende del modelo, el prompt y el esfuerzo de razonamiento, no del valor de temperatura. |

### Etiquetas heurísticas (no son tiers oficiales)

| Etiqueta (heurística) | Rango sugerido | Nota |
| --- | --- | --- |
| Muy determinista | 0.0–0.3 | Combínela con `seed` para mejorar reproducibilidad best-effort. |
| Equilibrada (valor actual de `call_ai` en 02-06) | ~0.7 | Valor por defecto usado en el código planeado. |
| Creativa | ~1.0–1.5 | Mayor diversidad; sin garantía de calidad. |
| Caótica (solo si la cuota lo permite) | ~2.0 | Máxima aleatoriedad; útil para explorar límites, no para producción. |

> Estas bandas son **heurísticas de trabajo**, no fronteras oficiales. Groq documenta `temperature` como `float` en el rango **0–2**.

## Intuición de muestreo y lo que la temperatura NO controla

`temperature` escala la entropía de la distribución de probabilidad antes de muestrear el siguiente token: valores bajos aplatan la distribución (más probable → más repetible), valores altos la aplanan (más diverso). Pero es un parámetro de **muestreo**, no de semántica.

| Lo que la temperatura NO controla | Por qué |
| --- | --- |
| Corrección factual | Depende del modelo y del conocimiento, no del muestreo. |
| Esfuerzo de razonamiento (`reasoning_effort`) | Eje **distinto** de `temperature`; en GPT-OSS es `low`/`medium`/`high`. |
| Creatividad garantizada | Mayor diversidad ≠ mejor o más creativo. |
| Determinismo garantizado | `temperature=0` es "más determinista", no idéntico; el backend puede cambiar. |

## Rango 0–2, bandas prácticas y top_p

- **Rango documentado:** `temperature` acepta `float` en **0–2** en `client.chat.completions.create` de Groq. Valores fuera de ese rango deben ser rechazados por la validación (ver plan de arquitectura).
- **Bandas prácticas:** véase la tabla heurística arriba. Úselas como punto de partida, no como regla.
- **`top_p` (núcleo):** parámetro de muestreo distinto, rango **0–1**. La `call_ai` planeada en 02-06 usa `top_p=0.9`. **No** cambie `temperature` y `top_p` simultáneamente; aisle efectos ajustando uno a la vez.
- **GPT-OSS y razonamiento:** el ejemplo oficial de razonamiento de Groq usa `temperature=0.6` y `top_p=0.95` con `openai/gpt-oss-20b`; esto ilustra una configuración válida, no un valor obligatorio.

## Reproducibilidad: seed, system_fingerprint y deriva

- **`seed` (int):** proporciona determinismo **best-effort**, no garantizado. La documentación oficial de prompting de Groq recomienda combinar `seed` con una temperatura baja (0.0–0.3) para mejorar la reproducibilidad, útil para depurar y mejorar prompts de forma iterativa.
- **`system_fingerprint`:** aparece en la respuesta (`response.system_fingerprint` si está disponible). Monitoree este valor para detectar cambios en el backend/modelo; una huella distinta puede explicar salidas diferentes aunque todo lo demás sea igual.
- **Condiciones para reproducir:** mismo `model`, mismos `messages`, mismos parámetros (`temperature`, `seed`, `top_p`…) y mismo backend.
- **Deriva de backend/modelo:** los snapshots del modelo cambian con el tiempo; aun con `seed`, la salida puede variar cuando Groq actualiza el backend. Por eso una sola muestra **nunca** es prueba estadística.

## Caveat de portabilidad entre proveedores/modelos

La semántica de `temperature` no es idéntica entre proveedores ni entre modelos. El mismo valor puede comportarse distinto en otro proveedor o en otro modelo de Groq. No asuma transferibilidad: el experimento de esta lección es válido para `openai/gpt-oss-20b` en Groq, no como regla universal.

## Experimento controlado y consciente de cuota

### Diseño del experimento

- **Modelo fijo:** `openai/gpt-oss-20b` (modelo de razonamiento; sus tokens de razonamiento cuentan dentro de `completion_tokens`).
- **Prompt/mensajes fijos:** una sola pregunta corta y determinista por corrida (p. ej. "Define 'muestreo' en una frase.").
- **Temperaturas:** `0.0`, `0.7`, `1.2`, con **una muestra en vivo por valor** por defecto. El `for temperature in temperatures` itera configuraciones distintas **una vez cada una**; no es un bucle de reintentos ni de muestreo repetido.
- **Opcional `2.0`:** solo si su cuota lo permite; no es obligatorio.
- **Una muestra es ilustrativa, no prueba estadística.** No realice llamadas repetidas, no agregue bucles, ni `sleep`/reintentos arbitrarios. Si alcanza un límite de tasa, deténgase y respete los límites (el SDK reintenta nativamente `RateLimitError`/`APIConnectionError` con backoff).

### Esquema de registro (sin response IDs)

| Campo | Descripción |
| --- | --- |
| `temperature` | Valor usado en la llamada. |
| `seed` | Valor de semilla fijado, o `—` si no se fijó. |
| `model` | `openai/gpt-oss-20b`. |
| `system_fingerprint` | De `response.system_fingerprint` (si disponible). |
| `prompt_tokens` | De `response.usage`. |
| `completion_tokens` | De `response.usage` (incluye tokens de razonamiento). |
| `total_tokens` | De `response.usage`. |
| `reasoning_tokens` | De `usage.completion_tokens_details.reasoning_tokens` (si disponible). |
| `estimated_theoretical_cost` | Estimación con tarifas de `settings` (`Decimal`); etiquetar `NOT BILLED`. |
| `output` | Texto de `choices[0].message.content`. |

> **Omisión explícita:** no registre `response.id` ni ningún identificador de respuesta.

### Free Plan y conciencia de tokens/costo

- El uso y las cuotas de Groq son **reales** aunque esté en Free Plan; el monto facturado puede ser cero dentro de los límites, pero **verifique los límites y precios actuales de su cuenta** en `https://console.groq.com/settings/limits` (no asuma $0 de forma universal más allá de su contexto actual).
- Los **tokens de razonamiento se cuentan dentro de `completion_tokens`** (y por ende de `total_tokens`); la salida visible puede ser corta mientras `completion_tokens` es mayor.
- La estimación de costo es **teórica a precio de lista**, no el cargo real; etiquétela como `NOT BILLED`.

## Plan de arquitectura (no implementado)

> Todo fragmento de esta sección es **PLANNED / pseudocódigo**. Ninguno existe aún; no se ha ejecutado `ruff`/`mypy`/`pytest` sobre ellos.

### `sampling.py` — `validate_temperature` (PLANNED)

```python
# PLANNED (pseudocódigo): src/python_applied_ai/sampling.py
# No existe aún. Se añade después de 02-06.

from __future__ import annotations

MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0


def validate_temperature(value: float) -> float:
    """Return value if within Groq's documented 0.0-2.0 range.

    Raises ValueError otherwise. Pure, provider-neutral guard.
    """
    if value < MIN_TEMPERATURE or value > MAX_TEMPERATURE:
        raise ValueError(
            f"temperature must be in [{MIN_TEMPERATURE}, {MAX_TEMPERATURE}], got {value}"
        )
    return value
```

### Extensión de `call_ai` con `temperature` (PLANNED)

Firma coherente con 02-06 (`call_ai(client, question, settings) -> ChatCompletion`); se añade `temperature: float = 0.7`.

```python
# PLANNED (pseudocódigo): extensión de call_ai definida en 02-06.
# El tipo exacto del cliente (`Groq`) se confirma en 02-06; aquí se asume
# el tipo del SDK de Groq. No inventamos un tipo final falso.
# No se ha ejecutado ruff/mypy/pytest sobre este fragmento.

from groq import Groq
from groq.types.chat import ChatCompletion

from python_applied_ai.config import Settings
from python_applied_ai.sampling import validate_temperature


def call_ai(
    client: Groq,
    question: str,
    settings: Settings,
    temperature: float = 0.7,
) -> ChatCompletion:
    """Call Groq chat completions and return the full response.

    Extiende la firma de 02-06 con `temperature` opcional (por defecto 0.7,
    coherente con el valor actual). El dominio no imprime ni llama a SystemExit.
    """
    return client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": question}],
        max_tokens=settings.llm_max_tokens,
        temperature=validate_temperature(temperature),
        top_p=0.9,
    )
```

### Harness de experimento separado (PLANNED)

```python
# PLANNED (pseudocódigo): harness de experimento, separado de call_ai.
# No forma parte del dominio; es una herramienta de estudio consciente de cuota.

from decimal import Decimal
from typing import Any

from groq import Groq

from python_applied_ai.config import get_settings
from python_applied_ai.hello_ai import call_ai
from python_applied_ai.cost import estimate_cost_usd


def run_temperature_sweep(
    client: Groq,
    question: str,
    temperatures: list[float],
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Itera cada valor de `temperatures` como una configuración de
    experimento distinta, con UNA muestra en vivo por valor.

    NO es un bucle de reintentos ni de muestreo repetido: cada temperatura
    se evalúa una sola vez. NO sleeps, NO retries arbitrarios. Añada `2.0`
    solo si la cuota lo permite.
    """
    settings = get_settings()
    rows: list[dict[str, Any]] = []
    # Cada temperatura es una configuración distinta del experimento:
    # se evalúa UNA vez (una muestra en vivo), no es reintento ni bucle de muestreo.
    for temperature in temperatures:
        response = call_ai(client, question, settings, temperature=temperature)
        usage = response.usage
        cost_text = "NOT BILLED (rates not configured)"
        if (
            usage is not None
            and settings.llm_input_rate_per_million is not None
            and settings.llm_output_rate_per_million is not None
        ):
            cost = estimate_cost_usd(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                input_rate_per_million=settings.llm_input_rate_per_million,
                output_rate_per_million=settings.llm_output_rate_per_million,
            )
            cost_text = f"{cost:.10f}"
        rows.append(
            {
                "temperature": temperature,
                "seed": seed,
                "model": response.model,
                "system_fingerprint": getattr(response, "system_fingerprint", None),
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": usage.completion_tokens if usage else None,
                "total_tokens": usage.total_tokens if usage else None,
                "reasoning_tokens": (
                    usage.completion_tokens_details.reasoning_tokens
                    if usage and usage.completion_tokens_details
                    else None
                ),
                "estimated_theoretical_cost": cost_text,
                "output": response.choices[0].message.content,
                # NOTA: no se registra response.id (omisión de IDs de respuesta).
            }
        )
    return rows
```

## Plan de TDD (RED → GREEN → offline)

Cero llamadas reales a la API en las pruebas.

### RED: pruebas de límites

```python
# PLANNED (pseudocódigo): tests/test_sampling.py — fase RED.
# No existe aún; estas pruebas fallan hasta implementar sampling.py.
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
```

### GREEN: implementación del helper

Implementar `validate_temperature` tal como se muestra en la sección de arquitectura (rechaza `<0` y `>2`, devuelve el valor en caso contrario). Tras implementarlo, las 6 pruebas anteriores pasan.

### Prueba offline con cliente falso (reenvío de temperature)

```python
# PLANNED (pseudocódigo): tests/test_call_ai_temperature.py — offline.
from unittest.mock import MagicMock

from python_applied_ai.hello_ai import call_ai  # con la extensión de temperatura


def test_call_ai_forwards_temperature() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock()
    settings = MagicMock()
    settings.llm_model = "openai/gpt-oss-20b"
    settings.llm_max_tokens = 256

    call_ai(fake_client, "hi", settings, temperature=1.2)

    fake_client.chat.completions.create.assert_called_once()
    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["temperature"] == 1.2
```

### Prueba del harness con cliente falso

```python
# PLANNED (pseudocódigo): tests/test_experiment_harness.py — offline.
from unittest.mock import MagicMock

from python_applied_ai.experiment_temperature import run_temperature_sweep


def _fake_response(content: str, fingerprint: str | None = "fp-abc") -> MagicMock:
    resp = MagicMock()
    resp.model = "openai/gpt-oss-20b"
    resp.system_fingerprint = fingerprint
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 20
    resp.usage.total_tokens = 30
    resp.usage.completion_tokens_details.reasoning_tokens = 5
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    return resp


def test_sweep_records_rows_without_network() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_response("a"),
        _fake_response("b"),
        _fake_response("c"),
    ]
    settings = MagicMock()
    settings.llm_model = "openai/gpt-oss-20b"
    settings.llm_max_tokens = 256
    settings.llm_input_rate_per_million = None
    settings.llm_output_rate_per_million = None

    rows = run_temperature_sweep(fake_client, "q", [0.0, 0.7, 1.2])
    assert len(rows) == 3
    assert rows[0]["temperature"] == 0.0
    # Sin IDs de respuesta en las filas.
    assert "id" not in rows[0]
```

## Procedimiento manual del experimento

1. Complete primero [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md) (define `call_ai`).
2. Añada `sampling.py` con `validate_temperature` y extienda `call_ai` con `temperature` (ver plan de arquitectura).
3. Cree el harness `experiment_temperature.py` por separado.
4. Ejecute **una** muestra en vivo por temperatura: `0.0`, `0.7`, `1.2`. Añada `2.0` solo si su cuota lo permite.
5. Registre cada fila con el esquema de la sección "Esquema de registro" (sin `response.id`).
6. Compare las salidas; no concluya patrones a partir de una sola muestra.

## Observaciones esperadas (sin prometer salidas exactas)

- A `temperature=0.0` la salida tiende a ser más estable entre corridas (con la misma `seed`/`system_fingerprint`), pero no idéntica garantizada.
- A `0.7` y `1.2` espera mayor variación de formulación; el contenido suele seguir siendo correcto para preguntas simples.
- Los `reasoning_tokens` aparecen dentro de `completion_tokens`; la salida visible puede ser corta.
- Si `system_fingerprint` cambia entre corridas, cualquier diferencia de salida puede deberse al backend, no solo a `temperature`.

## Preguntas de análisis

- ¿Varía la salida a `temperature=0.0` entre dos corridas con la misma `seed`? ¿Por qué?
- ¿Qué aporta `system_fingerprint` para interpretar las diferencias?
- ¿Por qué una sola muestra por temperatura no es evidencia estadística?
- ¿Cómo se relaciona (y se diferencia) `reasoning_effort` de `temperature`?

## Errores comunes

- Creer que `temperature=0` garantiza salida idéntica.
- Cambiar `temperature` y `top_p` a la vez y atribuir el efecto a uno solo.
- Hacer llamadas repetidas o bucles para "promediar" (consumo de cuota innecesario y no estadísticamente válido con una semilla).
- Registrar `response.id` o IDs de respuesta en el esquema.
- Asumir que los valores de temperatura se portan igual en otro proveedor/modelo.
- Tratar la estimación teórica de costo como el cargo real facturado.

## Checklist de aceptación

- [ ] `validate_temperature` rechaza `<0` y `>2`, y acepta `0`, `0.7`, `1.2`, `2`.
- [ ] `call_ai` acepta `temperature: float = 0.7` y lo reenvía a `client.chat.completions.create`.
- [ ] El harness de experimento está separado del dominio `call_ai`.
- [ ] La integración con `Settings` se difiere (aún no se añade temperatura a `Settings`).
- [ ] Las pruebas son 100% offline (MagicMock/fake client), cero llamadas reales.
- [ ] El experimento en vivo usa una muestra por temperatura; sin bucles ni `sleep`/reintentos.
- [ ] El esquema de registro omite `response.id` y cualquier ID de respuesta.
- [ ] `uv run ruff format --check .`, `ruff check .`, `mypy src` y `pytest` en verde (al implementar).
- [ ] [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md) está implementado antes de esta lección.

## Comandos de verificación

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
# Experimento manual (en vivo, fuera de las pruebas automatizadas):
uv run python -m python_applied_ai.experiment_temperature  # PLANNED, no existe aún
```

> El experimento en vivo es manual y consciente de cuota; no forma parte de la verificación automatizada (que debe ser offline).

## Siguiente paso

Implemente primero [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md); esta lección 02-07 depende de `call_ai`. El eje `reasoning_effort` (distinto de `temperature`) se cubre en la documentación oficial de razonamiento de Groq, no en este experimento.

La siguiente lección, [02-08-cli-chatbot-conversation-history.md](./02-08-cli-chatbot-conversation-history.md) (Planned), introduce la clase de dominio `ChatBot` con historial de conversación tipado; aún no está implementada.

## Referencias externas oficiales

- groq-python: https://github.com/groq/groq-python
- Documentación de Groq: https://console.groq.com/docs/quickstart
- Modelos y límites: https://console.groq.com/docs/models
- Modelo GPT-OSS 20B: https://console.groq.com/docs/model/openai/gpt-oss-20b
- Razonamiento (`reasoning_effort`, ejemplo con `temperature=0.6`/`top_p=0.95`): https://console.groq.com/docs/reasoning
- Prompting (`seed`, determinismo best-effort, `system_fingerprint`): https://console.groq.com/docs/prompting
- Límites de tasa: https://console.groq.com/docs/rate-limits
- Límites y precios de la cuenta: https://console.groq.com/settings/limits
