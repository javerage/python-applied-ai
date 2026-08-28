# Chatbot en CLI: uso y costo teórico de sesión (Parte 2)

> **Aviso de privacidad y procedencia:** esta es una adaptación original de conceptos. No reproduce transcripciones ni código de terceros y no contiene credenciales, tarifas privadas, identificadores de respuestas, datos multimedia ni rutas personales. Los fragmentos reflejan la implementación verificada; **no se realizó ninguna llamada real a la API**: toda la validación de esta lección es offline.

## Estado

**Completed** — segunda parte del proyecto de chatbot CLI. Requiere la implementación completada de [02-08-cli-chatbot-conversation-history.md](./02-08-cli-chatbot-conversation-history.md). Esta guía documenta el contrato ya implementado en `src/python_applied_ai/chatbot_cli.py` y verificado offline en `tests/test_chatbot_cli.py`.

Evidencia verificada (árbol limpio en HEAD `f696e22`, rama `origin/main`, antes de los docs):
- `ChatTurn` y `SessionStats` (`@dataclass(frozen=True, slots=True)`) ya definidos.
- API pública `stats()` y `reset_session()` implementadas.
- Costo teórico exacto con `Decimal` vía `estimate_cost_usd` (commit `ac63d90`).
- Commits relevantes: `4979ed3` (`ChatTurn`), `e777b77` (`SessionStats`/acumulación), `ac63d90` (costo `Decimal` exacto), `fd4bd5f` (`reset_session`), `f696e22` (caracterización).
- `uv run ruff format --check .` y `uv run ruff check .` limpios.
- `uv run mypy src tests` sin errores en 9 archivos.
- `uv run pytest tests/test_chatbot_cli.py -q` = **13 passed** (5 heredados de 02-08 + 8 agregados en esta lección).
- `uv run pytest -q` = **27 passed** (suite completa).
- Validación 100% offline: ninguna llamada en vivo a la API.

## Resultado (ya implementado)

El chatbot conserva estadísticas **solo de la sesión actual**: turnos exitosos, tokens de entrada, tokens de salida, tokens totales y, cuando existan tarifas configuradas, una estimación teórica con `Decimal`. La interfaz CLI para mostrar estos datos queda en [02-10-cli-chatbot-loop-and-integration.md](./02-10-cli-chatbot-loop-and-integration.md).

## Ruta de implementación

1. Se mantuvo `ChatBot` y el historial transaccional de 02-08.
2. `chat()` ahora devuelve `ChatTurn` (texto + `usage`) en lugar de `str`.
3. Las estadísticas se acumulan solo tras una respuesta exitosa.
4. Se reutiliza `estimate_cost_usd` y tarifas opcionales de `Settings`; nunca hardcodeadas ni `float`.
5. Todo probado offline con respuestas falsas y sin `.env` ni red.

## Alcance y no objetivos

| Incluido (implementado en esta lección) | Diferido a 02-10 o posterior |
| --- | --- |
| Contrato de resultado de un turno (`ChatTurn`) | Bucle `input()` y presentación terminal |
| Acumulación en memoria de uso/costo teórico | Cobro real, facturación o persistencia |
| API pública `stats()` y `reset_session()` | Ventanas de contexto, resumen o RAG |
| Pruebas unitarias offline | Llamadas reales para provocar errores |

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

## Acumulación atómica

Tras obtener una `ChatCompletion` exitosa, el chatbot sigue este orden:

1. Extraer `text = response.choices[0].message.content or ""`.
2. Crear el mensaje `assistant` y el `ChatTurn(text=text, usage=response.usage)`.
3. Calcular los nuevos totales candidatos sin mutar el estado actual.
4. Confirmar juntos historial, contador de turnos y estadísticas.
5. Retornar el `ChatTurn`.

Una `APIConnectionError` u otra excepción tipada se propaga desde 02-08: no suma tokens, costo ni turnos, y no altera el historial ni `stats()`.

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

## Contrato de estadísticas y reset

- `stats() -> SessionStats`: devuelve una **snapshot inmutable** del estado actual de la sesión. Es una API pública; el bucle de 02-10 la invocará para presentar el resumen.
- `reset_session() -> None`: restaura el chatbot a su estado inicial: conserva solo el mensaje `system` y reinicia historial y estadísticas. El futuro `main` no debe modificar `bot.history` directamente.
- `turn_count` aumenta una vez por cada completación exitosa, incluso si el contenido visible es `""` (contrato de 02-08).
- Los acumulados de tokens solo aumentan cuando `usage` está disponible.
- Los valores son de una ejecución del proceso; no se persisten ni representan facturación real.

Estado inicial/reset de costo (método interno `_build_initial_stats`):

```python
def _build_initial_stats(self) -> SessionStats:
    """Build a zeroed session snapshot with rate-aware cost."""

    both_rates_configured = (
        self.settings.llm_input_rate_per_million is not None
        and self.settings.llm_output_rate_per_million is not None
    )
    initial_cost = Decimal("0") if both_rates_configured else None

    return SessionStats(
        turn_count=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        theoretical_cost_usd=initial_cost,
    )
```

`reset_session` reutiliza ese mismo constructor:

```python
def reset_session(self) -> None:
    """Restore the chatbot to its initial session state."""

    system_message = self._build_system_message()
    initial_stats = self._build_initial_stats()

    self.history[:] = [system_message]
    self._stats = initial_stats
```

### Clarificación de costo

- **Falta alguna tarifa** (`input_rate` o `output_rate` es `None`): `theoretical_cost_usd` es `None`, no un precio inventado.
- **Ambas tarifas configuradas** y uso cero, o tras `reset_session()`: `Decimal("0")`.
- Los valores acumulados son **estimaciones de precio de lista teórico**, no una factura ni cobro real. No se documentan tarifas privadas ni se realizan llamadas para medir costo.

## Plan de pruebas offline

Todos los casos usan `MagicMock`, `cast(Groq, ...)`, `Settings.model_construct` solo en tests y una `ChatCompletion` falsa con uso en memoria. El archivo `tests/test_chatbot_cli.py` tiene **13** pruebas (5 heredadas de 02-08 + 8 de esta lección); la suite completa es **27**.

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
- No imprimir estadísticas desde el dominio: 02-10 decide el formato de presentación (`format_stats`).
- `max_tokens` sigue deprecado por el SDK en favor de `max_completion_tokens`; esta lección no cambia el parámetro sin una migración verificada.

## Checklist de aceptación

- [x] `ChatTurn` separa texto y uso de proveedor.
- [x] `SessionStats` representa acumulados de una sola sesión.
- [x] La acumulación ocurre solo tras completación exitosa.
- [x] Faltan tarifas → costo `None`, no un precio inventado.
- [x] Se reutiliza `estimate_cost_usd` con `Decimal`.
- [x] Existe reset público (`reset_session()`) que conserva el mensaje `system`.
- [x] `stats()` expone una snapshot inmutable de la sesión.
- [x] Pruebas offline cubren éxito, tarifas ausentes, error, vacío, reset y caracterización de costo exacto.
- [x] Ruff, mypy y pytest pasan (13 pruebas del chatbot, 27 en total).

## Comandos de verificación (ejecutados)

```bash
uv run ruff format --check .   # 19 files already formatted
uv run ruff check .             # All checks passed!
uv run mypy src tests           # Success: no issues found in 9 source files
uv run pytest tests/test_chatbot_cli.py -q   # 13 passed
uv run pytest -q                # 27 passed
```

## Siguiente paso

El contrato de 02-09 está implementado y verificado offline. [02-10-cli-chatbot-loop-and-integration.md](./02-10-cli-chatbot-loop-and-integration.md) (Planificado) conectará las APIs públicas (`chat`, `stats`, `reset_session`) con una terminal interactiva y definirá `format_stats`/el bucle `run_cli`.

## Referencias oficiales

- Groq Python SDK y tipos: https://github.com/groq/groq-python
- Chat completions de Groq: https://console.groq.com/docs/chat
