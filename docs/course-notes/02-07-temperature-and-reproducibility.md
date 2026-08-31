# Temperatura y reproducibilidad con Groq

> **Aviso de derechos y privacidad:** Esta guía es una adaptación original basada en conceptos de un curso de pago, no una reproducción de su transcripción. No incluye texto literal de lecciones, identificadores de cuentas/proyectos o de medios (p. ej. Wistia), URLs de medios, metadatos de respuesta, marcas de tiempo, identificadores de respuesta, claves de API, valores de `.env`, tarifas privadas ni rutas personales. Las referencias apuntan únicamente a documentación oficial de Groq.

## Estado

**Completed — etapa 6 de 9.** Parte de los 14 tests de 02-06 y añade configuración productiva `LLM_TEMPERATURE`, validación provider-neutral, reenvío de `temperature`/`seed` y un harness inmutable. Esta etapa aporta 32 casos offline y deja el checkpoint acumulado en **46 tests**. El experimento live es opcional y no se ejecutó.

## Objetivo de aprendizaje

Comprender qué controla realmente `temperature` en Groq, por qué `temperature=0` no garantiza salida idéntica, cómo aproximar la reproducibilidad con `seed` y `system_fingerprint`, y cómo ejecutar un experimento controlado y consciente de cuota sobre `openai/gpt-oss-20b` sin reclamar prueba estadística ni realizar llamadas repetidas.

## Ruta rápida

1. (Hecho) [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) completo — medición de tokens y costo teórico.
2. (Hecho) [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md) completado — define `call_ai`.
3. (Hecho) `src/python_applied_ai/sampling.py` valida valores finitos entre `0.0` y `2.0`, ambos inclusive.
4. (Hecho) `call_ai` reenvía `temperature` y `seed`; `experiment_temperature.py` pre-valida toda la secuencia y produce filas inmutables.
5. (Hecho) Ruff, mypy y los **46 tests acumulados** pasan sin red ni consumo de cuota.

## Integración productiva de `LLM_TEMPERATURE`

Esta etapa elimina la temperatura como decisión dispersa. La configuración final sigue una sola ruta:

```text
.env → Settings.llm_temperature → validate_temperature → Groq
```

Añada a `.env.example` y al `.env` privado:

```dotenv
LLM_TEMPERATURE=0.7
```

En `Settings`, el valor se valida como finito y dentro del rango inclusivo `0..2`:

```python
from typing import Annotated

from pydantic import Field

llm_temperature: Annotated[
    float,
    Field(ge=0.0, le=2.0, allow_inf_nan=False),
] = 0.7
```

`hello_ai.main` entrega `settings.llm_temperature` a `call_ai`; la validación pura se repite en el límite del SDK. En 02-08, el nuevo `ChatBot` consumirá el mismo campo desde su primer diseño, evitando volver a introducir `0.7` como literal.

El `seed` permanece fuera de `Settings`: solo sirve al laboratorio para comparar configuraciones best-effort y no promete determinismo en conversaciones con historial cambiante.

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
| Equilibrada (valor actual de `call_ai`) | ~0.7 | Valor por defecto implementado. |
| Creativa | ~1.0–1.5 | Mayor diversidad; sin garantía de calidad. |
| Caótica (solo si la cuota lo permite) | ~2.0 | Máxima aleatoriedad; útil para explorar límites, no para producción. |

> Estas bandas son **heurísticas de trabajo**, no fronteras oficiales. Groq documenta `temperature` como `float` en el rango **0–2**.

## Intuición de muestreo y lo que la temperatura NO controla

`temperature` reescala la distribución de probabilidad antes de muestrear el siguiente token: valores bajos la vuelven más concentrada en los tokens probables; valores altos la aplanan y aumentan la diversidad. Es un parámetro de **muestreo**, no de semántica.

| Lo que la temperatura NO controla | Por qué |
| --- | --- |
| Corrección factual | Depende del modelo y del conocimiento, no del muestreo. |
| Esfuerzo de razonamiento (`reasoning_effort`) | Eje **distinto** de `temperature`; en GPT-OSS es `low`/`medium`/`high`. |
| Creatividad garantizada | Mayor diversidad ≠ mejor o más creativo. |
| Determinismo garantizado | `temperature=0` es "más determinista", no idéntico; el backend puede cambiar. |

## Rango 0–2, bandas prácticas y top_p

- **Rango documentado:** `temperature` acepta `float` en **0–2** en `client.chat.completions.create` de Groq. La validación implementada también rechaza `NaN` e infinitos.
- **Bandas prácticas:** véase la tabla heurística arriba. Úselas como punto de partida, no como regla.
- **`top_p` (núcleo):** parámetro de muestreo distinto, rango **0–1**. `call_ai` usa `top_p=0.9`. **No** cambie `temperature` y `top_p` simultáneamente; aisle efectos ajustando uno a la vez.
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
| `output` | Texto de `choices[0].message.content`. |

> **Omisión explícita:** no registre `response.id` ni ningún identificador de respuesta.

### Free Plan y conciencia de tokens/costo

- El uso y las cuotas de Groq son **reales** aunque esté en Free Plan; el monto facturado puede ser cero dentro de los límites, pero **verifique los límites y precios actuales de su cuenta** en `https://console.groq.com/settings/limits` (no asuma $0 de forma universal más allá de su contexto actual).
- Los **tokens de razonamiento se cuentan dentro de `completion_tokens`** (y por ende de `total_tokens`); la salida visible puede ser corta mientras `completion_tokens` es mayor.
- La estimación de costo es **teórica a precio de lista**, no el cargo real; etiquétela como `NOT BILLED`.

## Arquitectura implementada

### `sampling.py` — validación provider-neutral

```python
from __future__ import annotations

import math

MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0


def validate_temperature(value: float) -> float:
    """Return value if finite and inside the inclusive 0.0-2.0 range."""
    if math.isnan(value) or math.isinf(value):
        raise ValueError("temperature must be finite")
    if value < MIN_TEMPERATURE or value > MAX_TEMPERATURE:
        raise ValueError("temperature must be in [0.0, 2.0]")
    return value
```

El archivo real conserva mensajes de error más descriptivos. La idea esencial es validar **antes** de cualquier efecto externo.

### `call_ai` reenvía `temperature` y `seed`

La firma de 02-06 se extendió con valores opcionales, por lo que los callers de tres argumentos siguen funcionando.

```python
from groq import Groq
from groq.types.chat import ChatCompletion

from python_applied_ai.config import Settings
from python_applied_ai.sampling import validate_temperature


def call_ai(
    client: Groq,
    question: str,
    settings: Settings,
    temperature: float = 0.7,
    seed: int | None = None,
) -> ChatCompletion:
    """Call Groq and return the complete chat response."""
    return client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": question}],
        max_tokens=settings.llm_max_tokens,
        temperature=validate_temperature(temperature),
        seed=seed,
        top_p=0.9,
    )
```

### Harness de experimento separado

`TemperatureRow` es inmutable (`frozen=True`) y usa `slots=True`. El harness recibe todas sus dependencias por parámetro, valida **toda** la lista antes de la primera llamada y reenvía realmente la semilla al SDK.

```python
from dataclasses import dataclass

from groq import Groq

from python_applied_ai.config import Settings
from python_applied_ai.hello_ai import call_ai
from python_applied_ai.sampling import validate_temperature


@dataclass(frozen=True, slots=True)
class TemperatureRow:
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
        content = response.choices[0].message.content
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
```

El archivo real añade defensas para respuestas sin choices/mensaje. El esquema omite deliberadamente `response.id`, tokens y costo: esas métricas pertenecen a 02-05/02-09, no al contrato mínimo del experimento de muestreo.

## Evidencia TDD (RED → GREEN → REFACTOR)

Cero llamadas reales a la API en las pruebas. Las fases se conservaron como historial pedagógico; el estado final está verde.

### Fase 0: RED/GREEN — configuración productiva

`tests/test_config.py` aporta 7 casos: default `0.7`, valor configurable y rechazo parametrizado de valores menores que 0, mayores que 2, `NaN` e infinitos. Esto prueba la entrada desde configuración antes de conectar el dominio.

### Fase 1: RED — contrato de validación

**Archivo:** `tests/test_sampling.py` — 9 casos para límites, valor por defecto, valor intermedio, `NaN` e infinitos.

```python
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

**RED observado:** el módulo no existía. **GREEN final:** 9 pruebas pasan y los valores no finitos también se rechazan.

### Fase 2: GREEN — helper puro

**Archivo:** `src/python_applied_ai/sampling.py`. `validate_temperature` rechaza valores fuera de `0..2`, `NaN` e infinitos; devuelve sin alterar cualquier valor finito válido.

**Resultado:** las 9 pruebas de `test_sampling.py` pasan.

### Fase 3: GREEN/REFACTOR — `call_ai` + cliente falso

**Archivo:** `tests/test_call_ai_temperature.py` — 4 casos que verifican defaults, compatibilidad, validación previa y reenvío real de `temperature`/`seed`.

```python
from unittest.mock import MagicMock

from python_applied_ai.hello_ai import call_ai


def test_call_ai_forwards_temperature_and_seed() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock()
    settings = MagicMock()
    settings.llm_model = "openai/gpt-oss-20b"
    settings.llm_max_tokens = 256

    call_ai(fake_client, "hi", settings, temperature=1.2, seed=42)

    fake_client.chat.completions.create.assert_called_once()
    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["temperature"] == 1.2
    assert kwargs["seed"] == 42
```

**Resultado:** 4 pruebas pasan; un valor inválido falla antes de llamar al cliente.

### Fase 4: REFACTOR — harness con cliente falso

**Archivo:** `tests/test_experiment_harness.py` — 12 pruebas de filas, orden, semilla, fingerprint opcional, contenido vacío, inmutabilidad, ausencia de IDs y atomicidad de validación.

```python
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

    rows = run_temperature_sweep(
        fake_client,
        settings,
        "q",
        [0.0, 0.7, 1.2],
        seed=42,
    )
    assert len(rows) == 3
    assert rows[0].temperature == 0.0
    assert rows[0].seed == 42
```

**Resultado:** 12 pruebas pasan; toda temperatura se valida antes del primer efecto externo y cada configuración produce exactamente una llamada.

### No determinismo y límites del proveedor

- `temperature`: controla la entropía de muestreo; `0.0` reduce aleatoriedad pero **no** garantiza salida idéntica.
- `seed`: determinismo best-effort; combine con temperatura baja (0.0–0.3) para mejor reproducibilidad.
- `system_fingerprint`: monitoree `response.system_fingerprint` para detectar cambios de backend/modelo entre corridas.
- Límites del proveedor: `temperature` rango documentado 0–2; `top_p` rango 0–1. Valores fuera de rango deben ser rechazados por `validate_temperature`.
- Una sola muestra **nunca** es prueba estadística; el backend puede cambiar independientemente de `seed`.

## Procedimiento manual del experimento

1. Confirme que las pruebas offline y los checks de calidad están verdes.
2. Revise `sampling.py`, el forwarding de `call_ai` y la pre-validación del harness.
3. Configure cliente y `Settings` desde el límite de composición existente; nunca imprima la API key.
4. Opcionalmente ejecute **una** muestra en vivo por temperatura (`0.0`, `0.7`, `1.2`) desde una sesión controlada. Añada `2.0` solo si su cuota lo permite.
5. Registre únicamente los campos de `TemperatureRow`; nunca `response.id`.
6. Compare las salidas sin convertir una muestra por configuración en una conclusión estadística.

> El paso 4 **no se ejecutó** durante esta implementación. El harness no expone un CLI automático para impedir consumo accidental de cuota.

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

### Documentación y conceptos (completos)
- [x] `temperature` y su rango documentado 0–2 en Groq documentado.
- [x] `temperature=0` reduce aleatoriedad pero no garantiza salida idéntica.
- [x] `seed` ofrece determinismo best-effort; `system_fingerprint` permite detectar cambios de backend.
- [x] `top_p` es parámetro de muestreo separado (rango 0–1); no cambiar junto a `temperature`.
- [x] Experimento controlado: una muestra por temperatura, sin bucles ni `sleep`/reintentos.
- [x] Esquema de registro sin `response.id` ni ningún ID de respuesta.
- [x] Prerrequisitos 02-05 y 02-06 completados.

### Implementación, harness y tests
- [x] `validate_temperature` acepta `0`, `0.7`, `1.2`, `2` y rechaza rango inválido, `NaN` e infinitos.
- [x] `call_ai` acepta y reenvía `temperature: float = 0.7` y `seed: int | None = None`.
- [x] `Settings.llm_temperature` valida defaults, valores configurados, rango y números no finitos.
- [x] El harness está separado, recibe `Settings` y cliente por parámetro y pre-valida toda la secuencia.
- [x] `TemperatureRow` es inmutable y omite IDs de respuesta y secretos.
- [x] Las pruebas son 100 % offline; cero llamadas reales y cero cuota consumida.
- [x] El harness realiza una llamada por temperatura, sin `sleep`, retries ni loops ocultos.
- [x] Ruff, mypy, pytest y `git diff --check` están verdes.
- [ ] Experimento live opcional ejecutado manualmente (no requerido para cerrar la implementación).

## Comandos de verificación

```bash
uv run ruff format --check .
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q  # 46 tests acumulados en esta etapa
```

La verificación automatizada es 100 % offline. `experiment_temperature.py` es una API de estudio testeable, no un entrypoint que haga llamadas al importarlo o ejecutarlo accidentalmente.

## Siguiente paso

La configuración de muestreo queda integrada y el laboratorio está cubierto offline. Continúe con [02-08-cli-chatbot-conversation-history.md](./02-08-cli-chatbot-conversation-history.md), que construye `ChatBot` usando `settings.llm_temperature` desde el primer turno.

## Referencias externas oficiales

- groq-python: https://github.com/groq/groq-python
- Documentación de Groq: https://console.groq.com/docs/quickstart
- Modelos y límites: https://console.groq.com/docs/models
- Modelo GPT-OSS 20B: https://console.groq.com/docs/model/openai/gpt-oss-20b
- Razonamiento (`reasoning_effort`, ejemplo con `temperature=0.6`/`top_p=0.95`): https://console.groq.com/docs/reasoning
- Prompting (`seed`, determinismo best-effort, `system_fingerprint`): https://console.groq.com/docs/prompting
- Límites de tasa: https://console.groq.com/docs/rate-limits
- Límites y precios de la cuenta: https://console.groq.com/settings/limits
