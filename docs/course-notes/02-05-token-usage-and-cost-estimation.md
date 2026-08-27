# Uso de tokens y estimación de costo con Groq: inspección de uso, metadatos y diseño de costo neutral al proveedor

> **Aviso de derechos y privacidad:** Este documento es una nota de estudio independiente que resume objetivos de aprendizaje y decisiones originales de implementación. No reproduce transcripciones de cursos de pago ni material con derechos de autor. No incluye claves de API reales, datos personales ni activos de video.

## Estado

**Implementación: Completed; Documentación: Completed; Cierre Git local (commit): Completed** — el prerrequisito [02-04-first-groq-api-call.md](./02-04-first-groq-api-call.md) está completo (llamada en vivo Groq + tarea de tres lenguas). Tanto la fase **requerida** (reporte de tokens/metadatos sobre el MISMO `response`) como la fase **opcional** (estimación de costo `Decimal` en `cost.py` + `tests/test_cost.py`) están **implementadas y verificadas en vivo**. `report_usage(response, settings)` imprime `response.id`, `response.model`, `response.usage` y una estimación teórica de costo, con guardas `is None` para `usage` y `completion_tokens_details`, y la función pura `estimate_cost_usd(...)` recibe las tarifas por parámetro con guardas contra valores negativos. Las tarifas opcionales tipadas se configuran mediante los placeholders en blanco `LLM_INPUT_RATE_PER_MILLION=` / `LLM_OUTPUT_RATE_PER_MILLION=` de `.env.example` (decisión #8684); los valores reales privados viven solo en `.env` ignorado por Git; no hay precios numéricos rastreados ni hardcodeados. **Cierre Git local realizado en `d35af37`** (`feat: add Groq token usage, cost estimation, and course notes`), que incluye el código y esta nota de estudio. **La sincronización remota está pendiente**: `origin/main` está actualmente un commit por detrás de `main` local; el `push` aún no se ha ejecutado.

## Objetivo de aprendizaje

Inspeccionar, tras una llamada a la API de Groq, los metadatos de respuesta (`response.id`, `response.model`) y las métricas de uso (`prompt_tokens`, `completion_tokens`, `total_tokens`, y opcionalmente `completion_tokens_details.reasoning_tokens`); comprender cómo los modelos de razonamiento afectan el recuento de tokens de completion; y diseñar una estimación de costo teórica, neutral al proveedor, sin hardcodear tarifas ni secretos, distinguiendo claramente el uso real del costo facturado.

## Ruta rápida

1. (Hecho) [02-04-first-groq-api-call.md](./02-04-first-groq-api-call.md) (`config.py` y `hello_ai.py`) completo — prerrequisito.
2. (Hecho — fase requerida) `hello_ai.py` ampliado: `main` hace una sola llamada y `report_usage(response, settings)` imprime `response.id`, `response.model` y `response.usage` (guardas `usage is None` y `completion_tokens_details is not None`) y, si hay tarifas configuradas, la estimación `NOT BILLED`. Verificado en vivo.
3. (Hecho — fase opcional) `src/python_applied_ai/cost.py` creado con la función pura `estimate_cost_usd(prompt_tokens, completion_tokens, input_rate_per_million, output_rate_per_million) -> Decimal` (guardas contra valores negativos) y `tests/test_cost.py` con 7 pruebas puras sin red (ejemplo normal, cero tokens, precisión/redondeo, parámetros negativos). El repositorio completo pasa 8 pruebas en total (7 de `tests/test_cost.py` + 1 preexistente `tests/test_package.py`). La función recibe tarifas por parámetro; las tarifas opcionales tipadas se cargan desde `.env.example` (placeholders en blanco, decisión #8684) vía `Settings`, con `env_ignore_empty=True` para que los blancos sean `None`. `ruff format .`, `ruff check .`, `mypy src` y `pytest` pasan.
4. (Hecho) Comprobaciones ejecutadas: `ruff format .`, `ruff check .`, `mypy src` (strict) y `pytest` (8 pruebas en total del repositorio: 7 de `tests/test_cost.py` + 1 preexistente `tests/test_package.py`) sin errores; ejecución en vivo exitosa.
5. (Hecho) Checklist de aceptación diligenciado: ítems de reporte, estimación, guardas, configuración tipada, gates de calidad y sin secretos en `[x]`.

## Resumen del concepto del instructor

La lección original "Uso de tokens y estimación de costo" del curso enseña a: crear un script que salude en tres lenguas, imprimir la respuesta directa, y luego leer `prompt_tokens`, `completion_tokens`, `total_tokens`, el `id` de la respuesta y el `model`, para finalmente estimar el costo de entrada/salida con tarifas por millón de tokens. Esta nota preserva ese flujo de aprendizaje y lo adapta a Groq con un diseño neutral al proveedor, reutilizando la única llamada ya existente. No se reproduce el texto del curso.

## Nuestra adaptación Groq y tabla de mapeo

| Concepto (OpenAI original) | Adaptación Groq |
| --- | --- |
| SDK `openai`, `CompletionUsage` | SDK `groq`, `groq.types.completion_usage.CompletionUsage` (mismo contrato compatible) |
| `response.usage` (requerido en OpenAI) | `response.usage` es `Optional[CompletionUsage]` en Groq 1.7.0 — proteja con `is None` |
| `response.usage.prompt_tokens` / `completion_tokens` / `total_tokens` | Idénticos en nombre y tipo (`int`) |
| `response.id`, `response.model` | Idénticos en nombre y tipo (`str`, no opcionales) |
| `completion_tokens_details.reasoning_tokens` (OpenAI) | Disponible en Groq 1.7.0 cuando `completion_tokens_details` está presente (opcional) |
| Tarifas de lista de OpenAI `gpt-4o-mini` | Tarifas de lista de Groq, **suministradas vía `Settings`** (placeholders en blanco en `.env.example`, decisión #8684; no hardcodeadas) |
| Estimación de costo con `float` | Estimación con `Decimal` y tasas por parámetro (sin flotante binario) |

## Detalles técnicos: campos de uso de Groq (SDK 1.7.0 instalado)

Verificado contra el paquete `groq` **instalado** (v1.7.0 en `.venv`), no contra la autodocumentación de Context7, que estaba desactualizada para estos tipos:

- `ChatCompletion.usage` es `Optional[CompletionUsage]` (valor por defecto `None`). Por tanto la guarda `if usage is None:` es **necesaria y correcta**, no código muerto. Bajo `mypy --strict` (`warn-unreachable`) no emite advertencia de inalcanzable.
- `CompletionUsage` incluye:
  - `prompt_tokens: int`
  - `completion_tokens: int`
  - `total_tokens: int`
  - `completion_tokens_details: Optional[CompletionTokensDetails]` (con `reasoning_tokens: int`)
  - `prompt_tokens_details: Optional[PromptTokensDetails]` (con `cached_tokens`)
  - campos de tiempo opcionales: `completion_time`, `prompt_time`, `queue_time`, `total_time` (`float | None`)
- `ChatCompletion.id: str` — identificador de la completion (no opcional).
- `ChatCompletion.model: str` — modelo efectivamente usado (no opcional).
- Importación de tipos: `from groq.types.chat import ChatCompletion` y `from groq.types.completion_usage import CompletionUsage`.

### Guarda segura de `response.usage`

Dado que `usage` es `Optional`, la comprobación `is None` es obligatoria:

```python
    usage = response.usage
    if usage is None:
        print("Uso no disponible en esta respuesta.")
        return
    # A partir de aqui, mypy sabe que `usage` es CompletionUsage.
    print(usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)
```

### Tokens de razonamiento y `openai/gpt-oss-20b`

`openai/gpt-oss-20b` es un modelo de razonamiento. Los tokens de razonamiento **se cuentan dentro de** `completion_tokens` y, por ende, de `total_tokens`. Consecuencia práctica: la salida visible (el texto impreso) puede ser corta mientras `completion_tokens` es notablemente mayor. No asuma que el número de tokens de completion equivale al texto visible; use siempre `completion_tokens` como medida de consumo.

Si está presente, el desglose de razonamiento está en `usage.completion_tokens_details.reasoning_tokens`. Como `completion_tokens_details` es opcional, protéjalo antes de acceder:

```python
    details = usage.completion_tokens_details
    if details is not None:
        print(details.reasoning_tokens)
```

## Diseño recomendado: estimación de costo neutral al proveedor

**Implementado (fase opcional):** una función pura `estimate_cost_usd(prompt_tokens, completion_tokens, input_rate_per_million, output_rate_per_million) -> Decimal` en `src/python_applied_ai/cost.py`, separado de `hello_ai.py` para que la refactorización de manejo de errores de [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md) no colisione con él. Usa `Decimal` para evitar errores de redondeo de punto flotante binario y **no** conoce ningún proveedor ni tarifa concreta: la función recibe las tarifas por parámetro (y rechaza valores negativos con `ValueError`). Se acompaña de `tests/test_cost.py` con 7 pruebas puras sin red (el repositorio pasa 8 en total: 7 de `tests/test_cost.py` + 1 preexistente `tests/test_package.py`). `main` reutiliza el MISMO `response.usage` existente (sin segunda llamada ni cuota extra) y `report_theoretical_cost` etiqueta la salida como "THEORETICAL LIST-PRICE ESTIMATE — NOT BILLED". Las tarifas opcionales se leen de `Settings` (cargadas desde `.env.example` en blanco, decisión #8684), no hardcodeadas.

### Variables de precio en `.env.example` (decisión #8684)

**Decidido: placeholders en blanco, sin precios.** `.env.example` ahora contiene los placeholders proveedor-neutrales en blanco `LLM_INPUT_RATE_PER_MILLION=` y `LLM_OUTPUT_RATE_PER_MILLION=` (sin números de precio). Motivos y mecánica:

- `Settings` define `llm_input_rate_per_million: Decimal | None = None` y `llm_output_rate_per_million: Decimal | None = None` como campos opcionales tipados.
- `model_config` usa `env_ignore_empty=True`: los placeholders en blanco se ignoran y el campo queda `None` (sin valores numéricos rastreados). No hay precios hardcodeados ni constantes de tarifa en el código (principio de configuración neutral al proveedor #8641).
- Los valores reales (privados) de tarifa se mantienen **solo** en `.env`, que está ignorado por Git; nunca se commitean.
- `report_theoretical_cost` salta la estimación si alguna tarifa es `None` ("Skipped: token rates are not configured.").

### `config.py` — campos de tarifa opcionales tipados

```python
from decimal import Decimal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    llm_input_rate_per_million: Decimal | None = None
    llm_output_rate_per_million: Decimal | None = None
```

## Fragmentos incrementales (inglés)

### `hello_ai.py` — `report_usage`, `report_theoretical_cost`, `format_usd` (implementado)

> Reutiliza el MISMO objeto `response` de la única llamada existente en `hello_ai.py`; `main` hace una sola `client.chat.completions.create` y luego `report_usage(response, settings)`. `response.id` se imprime pero **no se almacena** en ninguna variable.

```python
from decimal import Decimal

from groq.types.chat import ChatCompletion
from groq.types.completion_usage import CompletionUsage

from python_applied_ai.config import Settings
from python_applied_ai.cost import estimate_cost_usd


def format_usd(cost: Decimal) -> str:
    """Format a Decimal cost without losing precision."""
    formatted = format(cost, "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted or "0"


def report_theoretical_cost(usage: CompletionUsage, settings: Settings) -> None:
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


def report_usage(response: ChatCompletion, settings: Settings) -> None:
    """Report token usage statistics and theoretical cost from an EXISTING response."""
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
```

### `cost.py` — `estimate_cost_usd` (implementado)

> Módulo real `src/python_applied_ai/cost.py`, separado de `hello_ai.py`. Función pura, sin red y sin conocimiento de proveedor: recibe las tarifas por parámetro y rechaza valores negativos.

```python
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
```

**Fase requerida (reporte de tokens/metadatos):** en `main()` de `hello_ai.py`, tras la única llamada existente que ya produce `response`, se llama `report_usage(response, settings)` (verificado en vivo). No cree un segundo `client.chat.completions.create` ni un archivo `hello_languages.py`.

**Fase de aprendizaje opcional (costo):** `estimate_cost_usd(...)` ya vive en `cost.py` y es una función pura; `report_theoretical_cost` la invoca reutilizando el MISMO `response.usage` (sin segunda llamada) con las tarifas opcionales tipadas de `settings` (cargadas desde `.env.example` en blanco, vía `env_ignore_empty`). En ejecución en vivo se imprimió `Estimated cost: USD 0.0000312` bajo el rótulo `THEORETICAL LIST-PRICE ESTIMATE — NOT BILLED`. El resultado es una **estimación teórica a precio de lista**, no el costo facturado real; etiquételo como tal.

## Sección teórica de costo (opcional): distinga cuatro conceptos

| Concepto | Qué es | Estado en Free Plan |
| --- | --- | --- |
| Métricas de uso (`*_tokens`) | Recuento real devuelto por la API | **Reales** y reportadas |
| Cuotas de límite de tasa | RPM/RPD/TPM/TPD por organización | **Reales**, aplicables |
| Estimación de costo a precio de lista | Cálculo teórico con tarifas por millón | **Teórica**, no facturada |
| Monto facturado real | Lo que se cobra al terminar el periodo | **Cero** dentro de los límites del Free Plan |

Aclare: el Free Plan de Groq tiene límites reales y el uso se mide; la estimación a precio de lista es solo teórica y, dentro de los límites del Free Plan, el monto facturado real es **cero**. No afirme que el uso en Free Plan es ilimitado: hay cuotas y pueden cambiar; consulte `https://console.groq.com/settings/limits` y `https://console.groq.com/docs/models`.

### Ejemplo numérico ilustrativo (con variables placeholder)

Suponga —solo a efectos ilustrativos, no use estas cifras como precios reales— `prompt_tokens=40`, `completion_tokens=120`, y tarifas placeholder `input_rate = Decimal("0.000100")`, `output_rate = Decimal("0.000300")` USD por millón:

```python
cost = estimate_cost_usd(40, 120, Decimal("0.000100"), Decimal("0.000300"))
# Arithmetic: 40*0.0001/1e6 = 4e-9 ; 120*0.0003/1e6 = 3.6e-8 ; sum = 4.0e-8
assert cost == Decimal("4.0E-8")
```

El resultado es **ilustrativo**; sustituya las tarifas por valores reales de su fuente de precios externa antes de cualquier conclusión. No confunda esta estimación teórica con el costo facturado real (cero dentro del Free Plan).

## Privacidad y diagnóstico de `response.id`

- `response.id` es un identificador de la completion, útil para logs y diagnóstico de soporte. Es **seguro registrarlo en general**.
- No lo combine con la API key (`GROQ_API_KEY`), con el contenido de prompts sensibles, ni con otros secretos en el mismo mensaje de log.
- Nunca imprima ni registre la longitud o el valor de `GROQ_API_KEY`; el placeholder de `.env.example` permanece en blanco (`GROQ_API_KEY=`).
- En esta implementación `response.id` se imprime en vivo (`Response ID: ...`) pero **no se almacena** en ninguna variable ni se repite en este documento.

## Tarea (homework)

Reutilice el módulo `hello_ai.py` ya existente (que saluda en tres lenguas tras `02-04`) y el reporte de uso/metadatos y la estimación teórica descritos arriba, sobre el MISMO `response`. No duplique el script completo; `main()` llama `report_usage(response, settings)`, que a su vez invoca `report_theoretical_cost` → `estimate_cost_usd(...)` con las tarifas opcionales tipadas de `settings` (cargadas desde `.env.example` en blanco).

## Verificación

Estos comandos se ejecutaron tras extender `hello_ai.py` con el reporte y añadir `cost.py` + `tests/test_cost.py`. Ambas fases están **verificadas**; los siguientes resultados se observaron en ejecución en vivo y en los gates de calidad.

```bash
uv run python -m python_applied_ai.hello_ai
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
```

- `uv run python -m python_applied_ai.hello_ai` imprime la respuesta, los metadatos de uso y la estimación `NOT BILLED` (si hay tarifas), reutilizando el mismo `response`.
- `ruff format .` y `ruff check .` sin errores.
- `mypy` (modo strict, con `warn-unreachable`) sin errores de tipos.
- `pytest` pasa las 7 pruebas de `tests/test_cost.py` (comportamiento puro de `estimate_cost_usd`); en total el repositorio pasa 8 pruebas (7 de `tests/test_cost.py` + 1 preexistente `tests/test_package.py`). `report_usage` se verificó en vivo, no tiene prueba unitaria propia.

### Evidencia de tokens en vivo (fase requerida + estimación opcional)

Ejecución en vivo con modelo `openai/gpt-oss-20b` (modelo de razonamiento) sobre el MISMO `response`; `report_theoretical_cost` imprimió la estimación etiquetada `NOT BILLED`:

| Métrica | Última ejecución | Ejecución previa |
| --- | --- | --- |
| `response.model` | `openai/gpt-oss-20b` | `openai/gpt-oss-20b` |
| `prompt_tokens` | 84 | 84 |
| `completion_tokens` | 83 | 110 |
| `total_tokens` | 167 | 194 |
| `completion_tokens_details.reasoning_tokens` | 60 | 87 |

**Variabilidad de razonamiento:** los tokens de razonamiento cambian entre ejecuciones (60 vs 87) porque la salida de razonamiento del modelo es variable; por eso `completion_tokens` (83 vs 110) y `total_tokens` (167 vs 194) también varían. No trate una sola tabla como universal. Invariantes que SÍ se mantienen: `prompt_tokens + completion_tokens = total_tokens`, y `reasoning_tokens <= completion_tokens`. Los tokens de razonamiento se cuentan dentro de `completion_tokens`, lo que explica que la salida visible sea corta mientras el recuento de completion es mayor. `response.id` se imprime en vivo pero **no se almacena** en ninguna variable ni se repite aquí.

## Checklist de aceptación

- [x] `02-04` implementado (prerrequisito desbloqueado). Ver [02-04-first-groq-api-call.md](./02-04-first-groq-api-call.md).
- [x] `hello_ai.py` reporta `response.id`, `response.model` y `response.usage` reutilizando el MISMO `response` (una sola llamada).
- [x] Se protege `response.usage is None`.
- [x] Se protege `completion_tokens_details is not None` antes de `reasoning_tokens`.
- [x] `estimate_cost_usd(...)` en `cost.py` usa `Decimal`, recibe tarifas por parámetro y rechaza valores negativos; `tests/test_cost.py` (7 pruebas) puro sin red — **hecho**. El repositorio completo pasa 8 pruebas en total (7 de `tests/test_cost.py` + 1 preexistente `tests/test_package.py`).
- [x] `config.py` expone `llm_input_rate_per_million` / `llm_output_rate_per_million` (`Decimal | None`) con `env_ignore_empty=True`; `.env.example` trae placeholders en blanco (decisión #8684).
- [x] `main()` llama a `report_usage(response, settings)`, que imprime la estimación `THEORETICAL LIST-PRICE ESTIMATE — NOT BILLED` (sin almacenar `response.id`).
- [x] No hay precios numéricos hardcodeados; `.env.example` solo lleva placeholders en blanco y los valores reales viven en `.env` ignorado.
- [x] `uv run ruff format .`, `ruff check .`, `mypy src` (strict) y `pytest` (8 pruebas en total del repositorio: 7 de `tests/test_cost.py` + 1 preexistente `tests/test_package.py`) sin errores. Nota: `report_usage` se verificó en vivo; no tiene prueba unitaria propia.
- [x] No se commitea `.env` ni secretos.

## Decisiones, trade-offs y errores comunes

- **`usage` ES `Optional[CompletionUsage]` en Groq 1.7.0 instalado**: la guarda `is None` es **necesaria**, no defensiva-muerta. Verificado contra el paquete instalado, no contra los autodocs de Context7 (que estaban desactualizados).
- **`completion_tokens_details` SÍ está disponible**: es `Optional[CompletionTokensDetails]` con `reasoning_tokens: int`. Protéjalo con `if details is not None` antes de acceder. `completion_tokens` sigue siendo el total autoritativo (incluye tokens de razonamiento).
- **`Decimal`, no `float`**: el punto flotante binario introduce errores de redondeo en ejemplos de facturación; use `Decimal` con tasas por millón. `estimate_cost_usd` además rechaza valores negativos (`ValueError`).
- **Una sola llamada**: reutilice el `response` existente; no cree un segundo `client.chat.completions.create` ni un `hello_languages.py` separado.
- **Tarifas externas/tipadas, sin precios rastreados**: la función pura recibe tarifas por parámetro; `Settings` carga tarifas opcionales desde `.env.example` en blanco (decisión #8684) con `env_ignore_empty=True`. Nunca hardcodee precios de proveedor en la aplicación ni commitee valores reales en `.env` (configuración neutral al proveedor #8641).
- **Free Plan ≠ ilimitado**: el uso y las cuotas son reales; la estimación a precio de lista es teórica y el costo facturado real = 0 dentro de límites, pero las cuotas existen y cambian.
- **`response.id` se imprime, no se almacena**: útil para diagnóstico, pero no se guarda en variables ni logs persistentes combinado con secretos.

## Estado actual y siguiente paso

La fase **requerida** (reporte de tokens/metadatos con `report_usage(response, settings)`) y la fase **opcional** (estimación de costo `Decimal` en `cost.py` + `tests/test_cost.py`, 7 pruebas) están **completadas y verificadas en vivo**; el repositorio completo pasa 8 pruebas en total (7 de `tests/test_cost.py` + 1 preexistente `tests/test_package.py`).; el prerrequisito [02-04-first-groq-api-call.md](./02-04-first-groq-api-call.md) sigue completo. **Implementación, documentación y cierre Git local completados** en el commit `d35af37` (`feat: add Groq token usage, cost estimation, and course notes`). **La sincronización remota está pendiente**: `origin/main` está un commit por detrás de `main` local; el `push` no se ha ejecutado. **El siguiente paso es commitear esta corrección de documentación, luego hacer `push` de ambos commits, y a continuación iniciar** [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md) (manejo tipado y testeable de errores de la API de Groq), que se mantiene **Planned** y secuenciada después de este paso.

## Mensaje de commit sugerido

El cierre de la lección ya se realizó en `d35af37` (`feat: add Groq token usage, cost estimation, and course notes`), que incluye el código y esta nota de estudio. La reconciliación de estado de este documento con `d35af37` queda pendiente de su propio commit.

Para esta corrección de documentación:

```text
docs: reconcile 02-05 status with local commit d35af37
```

**La sincronización remota sigue pendiente**: `origin/main` está un commit por detrás de `main` local. Tras commitear esta corrección, haga `push` de ambos commits (`d35af37` y la corrección) y luego inicie [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md).

## Referencias externas oficiales

- groq-python: https://github.com/groq/groq-python
- Documentación de Groq: https://console.groq.com/docs/quickstart
- Modelos y límites: https://console.groq.com/docs/models
- Límites de tasa: https://console.groq.com/docs/rate-limits
- Límites de la cuenta: https://console.groq.com/settings/limits
- Modelo: https://console.groq.com/docs/model/openai/gpt-oss-20b
