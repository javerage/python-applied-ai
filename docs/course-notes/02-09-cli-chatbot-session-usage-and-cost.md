# Chatbot en CLI: uso y costo teórico de sesión (Parte 2)

> **Aviso de privacidad y procedencia:** esta es una adaptación original de conceptos. No reproduce transcripciones ni código de terceros y no contiene credenciales, tarifas privadas, identificadores de respuestas, datos multimedia ni rutas personales. Los fragmentos reflejan la implementación verificada; **no se realizó ninguna llamada real a la API**: toda la validación de esta lección es offline.

## Estado

**Completed — etapa 8 de 9.** Parte de los 51 tests de 02-08 y añade `ChatTurn`, `SessionStats`, acumulación atómica, costo teórico y reset. Incorpora 8 casos offline; el checkpoint acumulado queda en **59 tests**. El bucle CLI se reserva para 02-10.

Evidencia de esta etapa:
- `ChatTurn` y `SessionStats` (`@dataclass(frozen=True, slots=True)`) ya definidos.
- API pública `stats()` y `reset_session()` implementadas.
- Costo teórico exacto con `Decimal` vía `estimate_cost_usd`.
- Commits relevantes: `4979ed3` (`ChatTurn`), `e777b77` (`SessionStats`/acumulación), `ac63d90` (costo `Decimal` exacto), `fd4bd5f` (`reset_session`).
- `uv run ruff format --check .` y `uv run ruff check .` limpios.
- `uv run mypy src tests` sin errores en 9 archivos.
- `tests/test_chatbot_cli.py` alcanza **13 casos**: 5 de 02-08 + 8 de 02-09.
- `uv run pytest -q` alcanza **59 tests acumulados**.
- Validación 100% offline: ninguna llamada en vivo a la API.

## Resultado de la etapa

El chatbot conserva estadísticas **solo de la sesión actual**: turnos exitosos, tokens de entrada, salida y totales; cuando hay tarifas, añade una estimación teórica con `Decimal`. La presentación de estos datos se implementa después, en 02-10.

## Ruta de implementación

1. Se mantuvo `ChatBot` y el historial transaccional de 02-08.
2. `chat()` ahora devuelve `ChatTurn` (texto + `usage`) en lugar de `str`.
3. Las estadísticas se acumulan solo tras una respuesta exitosa.
4. Se reutiliza `estimate_cost_usd` y tarifas opcionales de `Settings`; nunca hardcodeadas ni `float`.
5. Todo probado offline con respuestas falsas y sin `.env` ni red.

## Alcance y no objetivos

| Incluido (implementado) | Completado en |
| --- | --- |
| Contrato de resultado de un turno (`ChatTurn`) | 02-09 |
| Acumulación en memoria de uso/costo teórico | 02-09 |
| API pública `stats()` y `reset_session()` | 02-09 |
| Bucle `input()` y presentación terminal (`run_cli`, `format_stats`) | 02-10 |
| Pruebas unitarias offline | 02-09 |

02-10 consumirá estas APIs públicas para construir el bucle interactivo y `format_stats`.

El costo calculado es una **estimación de precio de lista**, no una factura. Si faltan tarifas en la configuración, el costo teórico es desconocido (`None`), no cero.

## Contrato de resultado de un turno tipado

`ChatBot.chat()` devuelve `ChatTurn`. Así se mantiene texto y uso juntos sin confundirlos con una respuesta completa del SDK:

```python
# src/python_applied_ai/chatbot_cli.py

from dataclasses import dataclass
from decimal import Decimal

from groq.types.completion_usage import CompletionUsage


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """Represent one successful chatbot response."""

    text: str
    usage: CompletionUsage | None


@dataclass(frozen=True, slots=True)
class SessionStats:
    """Represent an immutable snapshot of chatbot session totals."""

    turn_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    theoretical_cost_usd: Decimal | None
```

Los consumidores (02-10) imprimen `turn.text` y usan `turn.usage` si lo necesitan. No se trata una cadena como si tuviera `.usage`.

## Acumulación atómica y nota técnica

`SessionStats` es una **snapshot inmutable** (`@dataclass(frozen=True, slots=True)`): el estado de la sesión se captura en un momento dado y no se muta después. La acumulación es atómica: solo se confirma tras un turno exitoso. Si `chat()` lanza una excepción tipada (p. ej. `APIConnectionError`), no se suman tokens, costo ni turnos, y `stats()` sigue devolviendo el snapshot anterior.

Tras obtener una `ChatCompletion` exitosa, el chatbot sigue este orden:

1. Extraer `text = response.choices[0].message.content or ""`.
2. Crear el mensaje `assistant` y el `ChatTurn(text=text, usage=response.usage)`.
3. Calcular los nuevos totales candidatos sin mutar el estado actual.
4. Confirmar juntos historial, contador de turnos y estadísticas.
5. Retornar el `ChatTurn`.

### Fórmula y tarifas

```python
# src/python_applied_ai/chatbot_cli.py — delega la aritmética al módulo ya verificado.
from python_applied_ai.cost import estimate_cost_usd

usage = response.usage

if usage is None:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
else:
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens
    total_tokens = usage.total_tokens

input_rate = self.settings.llm_input_rate_per_million
output_rate = self.settings.llm_output_rate_per_million

if input_rate is None or output_rate is None:
    next_cost = None
elif usage is None:
    next_cost = self._stats.theoretical_cost_usd
else:
    turn_cost = estimate_cost_usd(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        input_rate_per_million=input_rate,
        output_rate_per_million=output_rate,
    )
    prior_cost = self._stats.theoretical_cost_usd
    if prior_cost is None:
        prior_cost = Decimal("0")
    next_cost = prior_cost + turn_cost
```

Antes de llamar al estimador, ambas tarifas deben ser `Decimal` y no `None`. `reasoning_tokens`, cuando el proveedor los informa, forman parte del presupuesto de completación para GPT-OSS; no se suman otra vez al costo.

### `reset_session` y nota técnica

- `reset_session() -> None`: restaura el chatbot a su estado inicial; conserva solo el mensaje `system` y reinicia historial y estadísticas al snapshot cero.
- `turn_count` aumenta una vez por cada completación exitosa, incluso si el contenido visible es `""` (contrato de 02-08).
- Los acumulados de tokens solo aumentan cuando `usage` está disponible.
- Los valores son de una ejecución del proceso; no se persisten ni representan facturación real.
- **Separación dominio/presentación:** el dominio no imprime; el bucle de 02-10 consume `stats()` y `reset_session()` para renderizar.

### Clarificación de costo

- **Falta alguna tarifa** (`input_rate` o `output_rate` es `None`): `theoretical_cost_usd` es `None`, no un precio inventado.
- **Ambas tarifas configuradas** y uso cero, o tras `reset_session()`: `Decimal("0")`.
- Los valores acumulados son **estimaciones de precio de lista teórico**, no una factura ni cobro real. No se documentan tarifas privadas ni se realizan llamadas para medir costo.
- El tipo `Decimal` evita errores de redondeo monetario; las tarifas son `Decimal | None` opcionales en `Settings`; hoy no se exige su configuración.

## Plan de pruebas offline

Todos los casos usan `MagicMock`, `cast(Groq, ...)`, `Settings.model_construct` solo en tests y una `ChatCompletion` falsa. En este checkpoint, `tests/test_chatbot_cli.py` tiene **13 pruebas** y la suite acumulada, **59**.

| ID | Caso (función de prueba) | Comportamiento verificado |
| --- | --- | --- |
| T1 | `test_initial_history_has_system_message` (02-08) | El historial inicial es solo `system`. |
| T2 | `test_first_chat_round_returns_reply_and_commits_history` (02-08) | `chat` devuelve `ChatTurn.text` y confirma historial. |
| T3 | `test_second_chat_round_sends_prior_context` (02-08) | El segundo turno reenvía el contexto acumulado. |
| T4 | `test_api_failure_leaves_history_unchanged` (02-08) | El error propaga y no cambia historial ni `stats()`. |
| T5 | `test_empty_response_content_returns_and_stores_empty_string` (02-08) | `content None` → `text == ""`, cuenta como turno, costo `None`. |
| T6 | `test_chat_returns_text_and_provider_usage` | `ChatTurn` expone `text` y `usage`. |
| T7 | `test_fresh_chatbot_reports_zeroed_session_stats` | Chatbot nuevo: ceros y costo `None`. |
| T8 | `test_successful_turn_accumulates_session_stats_without_cost` | Un turno con uso suma tokens; costo sigue `None` sin tarifas. |
| T9 | `test_successful_turn_accumulates_exact_theoretical_cost` | Un turno con tarifas produce un `Decimal` exacto (caso de caracterización). |
| T10 | `test_reset_session_zeroes_stats_and_preserves_system_with_rates` | Reset con tarifas: ceros y `Decimal("0")`, conserva `system`. |
| T11 | `test_reset_session_zeroes_stats_and_preserves_system_without_rates` | Reset sin tarifas: ceros y costo `None`, conserva `system`. |
| T12 | `test_two_successful_turns_accumulate_exact_token_totals_and_cost` | Dos turnos suman tokens y `Decimal` exacto (caso de caracterización). |
| T13 | `test_failed_second_turn_preserves_accumulated_session_state` | Un segundo turno fallido conserva el estado del primero (caso de caracterización). |

Los datos `CompletionUsage` falsos incluyen `prompt_tokens`, `completion_tokens` y `total_tokens`. No se inventan precios del proveedor dentro de las pruebas: las tarifas sintéticas se pasan como `Decimal("1.0")`/`Decimal("2.0")` solo en el fixture de la prueba, sin relación con tarifas reales.

## Riesgos y decisiones

- No usar `len(history) // 2` para turnos: los mensajes de sistema, resets, contenido vacío y futuras herramientas invalidan esa inferencia.
- No usar `float`: la precisión monetaria pertenece a `Decimal` y al estimador existente.
- No imprimir estadísticas desde el dominio: la presentación (`format_stats`) corre en el bucle de 02-10; el dominio solo expone `stats()` y `reset_session()`.
- `max_tokens` sigue deprecado por el SDK en favor de `max_completion_tokens`; esta lección no cambia el parámetro sin una migración verificada.
- `SessionStats` snapshot inmutable: los acumulados se capturan por valor y no se mutan tras la creación; la acumulación atómica solo se produce tras un turno exitoso.

## Checklist de aceptación

- [x] `SessionStats` snapshot inmutable; acumulación atómica solo tras turno exitoso.
- [x] `reset_session()` conserva el mensaje `system` y reinicia al snapshot cero.
- [x] Faltan tarifas → costo `None`, no un precio inventado.
- [x] Se reutiliza `estimate_cost_usd` con `Decimal`.
- [x] Separación dominio/presentación: el dominio no imprime; `format_stats` corre en 02-10.
- [x] Pruebas offline cubren éxito, tarifas ausentes, error, vacío, reset y caracterización de costo exacto.
- [x] Ruff, mypy y pytest pasan (13 pruebas chatbot; 59 acumuladas).

## Comandos de verificación (ejecutados)

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest tests/test_chatbot_cli.py -q   # 13 tests en este checkpoint
uv run pytest -q                             # 59 tests acumulados
```

## Siguiente paso

El dominio ya devuelve `ChatTurn`, acumula snapshots inmutables y puede resetearse sin imprimir. Continúe con [02-10-cli-chatbot-loop-and-integration.md](./02-10-cli-chatbot-loop-and-integration.md) para conectar estas APIs al producto CLI final.

## Referencias oficiales

- Groq Python SDK y tipos: https://github.com/groq/groq-python
- Chat completions de Groq: https://console.groq.com/docs/chat
