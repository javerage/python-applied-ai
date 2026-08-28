# Chatbot en CLI: uso y costo teórico de sesión (Parte 2)

> **Aviso de privacidad y procedencia:** esta es una adaptación original de conceptos. No reproduce transcripciones ni código de terceros y no contiene credenciales, tarifas privadas, identificadores de respuestas, datos multimedia ni rutas personales.

## Estado

**Planned** — segunda parte del proyecto de chatbot CLI. Requiere la implementación completada de [02-08-cli-chatbot-conversation-history.md](./02-08-cli-chatbot-conversation-history.md). Esta guía define el siguiente cambio; no afirma que las clases, métodos o pruebas descritos existan todavía.

## Resultado esperado

El chatbot conservará estadísticas **solo de la sesión actual**: turnos exitosos, tokens de entrada, tokens de salida, tokens totales y, cuando existan tarifas configuradas, una estimación teórica con `Decimal`. La interfaz CLI para mostrar estos datos queda en 02-10.

## Ruta rápida

1. Mantener `ChatBot` y el historial transaccional de 02-08.
2. Reemplazar el retorno ambiguo de texto por un resultado tipado que mantenga texto y uso juntos.
3. Acumular estadísticas únicamente después de una respuesta exitosa.
4. Reutilizar `estimate_cost_usd` y tarifas opcionales de `Settings`; nunca hardcodear precios ni usar `float` para dinero.
5. Probar todo offline con respuestas falsas y sin `.env` ni red.

## Alcance y no objetivos

| Incluido | Diferido a 02-10 o posterior |
| --- | --- |
| Contrato de resultado de un turno | Bucle `input()` y presentación terminal |
| Acumulación en memoria de uso/costo teórico | Cobro real, facturación o persistencia |
| API pública de estadísticas y reinicio | Ventanas de contexto, resumen o RAG |
| Pruebas unitarias offline | Llamadas reales para provocar errores |

El costo calculado es una **estimación de precio de lista**, no una factura. Si faltan tarifas en la configuración, el costo teórico es desconocido (`None`), no cero.

## Decisión de diseño: resultado de turno tipado

`ChatBot.chat()` hoy devuelve `str`. Para registrar uso sin confundir texto con una respuesta completa del SDK, esta parte propone un cambio explícito y type-safe: devolver `ChatTurn`.

```python
# PLANNED: src/python_applied_ai/chatbot_cli.py
from dataclasses import dataclass
from decimal import Decimal

from groq.types import CompletionUsage


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """A successful chatbot turn and its optional provider usage."""

    text: str
    usage: CompletionUsage | None


@dataclass(frozen=True, slots=True)
class SessionStats:
    """In-memory totals for successful turns in one chatbot session."""

    turn_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    theoretical_cost_usd: Decimal | None
```

El cambio no es implícito: los consumidores de 02-10 deberán imprimir `turn.text`. Así se evita el error de tratar una cadena como si tuviera `.usage`.

## Acumulación atómica

Tras obtener una `ChatCompletion` exitosa, el chatbot debe seguir este orden:

1. Extraer `text = response.choices[0].message.content or ""`.
2. Crear el mensaje `assistant` y el `ChatTurn(text=text, usage=response.usage)`.
3. Calcular los nuevos totales candidatos sin mutar el estado actual.
4. Confirmar juntos historial, contador de turnos y estadísticas.
5. Retornar el `ChatTurn`.

Una `APIConnectionError` u otra excepción tipada se propaga desde 02-08: no debe sumar tokens, costo ni turnos, y tampoco debe alterar el historial.

### Fórmula y tarifas

```python
# PLANNED: delegar la aritmética al módulo ya verificado.
from python_applied_ai.cost import estimate_cost_usd

cost = estimate_cost_usd(
    prompt_tokens=usage.prompt_tokens,
    completion_tokens=usage.completion_tokens,
    input_rate_per_million=settings.llm_input_rate_per_million,
    output_rate_per_million=settings.llm_output_rate_per_million,
)
```

Antes de llamar al estimador, ambas tarifas deben ser `Decimal` y no `None`. `reasoning_tokens`, cuando el proveedor los informa, forman parte del presupuesto de completación para GPT-OSS; no se suman otra vez al costo.

## Contrato de estadísticas y reset

- `turn_count` aumenta una vez por cada completación exitosa, incluso si el contenido visible es `""` según el contrato de 02-08.
- Los acumulados de tokens solo aumentan cuando `usage` está disponible.
- El costo permanece `None` durante la sesión si no hay ambas tarifas; los tokens conocidos siguen siendo útiles.
- El reset debe ser una API pública, por ejemplo `bot.reset_session()`, que conserva el mensaje `system` y reinicia historial y estadísticas. El futuro `main` no debe modificar `bot.history` directamente.
- Los valores son de una ejecución del proceso; no se persisten ni representan facturación real.

## Plan de pruebas offline

Todos los casos usan `MagicMock`, `cast(Groq, ...)`, `Settings.model_construct` solo en tests y una `ChatCompletion` falsa con uso en memoria.

| Caso | Comportamiento esperado |
| --- | --- |
| Turno exitoso con tarifas | Incrementa turnos/tokens y acumula `Decimal` exacto. |
| Turno exitoso sin tarifas | Incrementa turnos/tokens; costo teórico es `None`. |
| Error del proveedor | Propaga la excepción y no cambia historial ni estadísticas. |
| Contenido `None` | Cuenta como turno exitoso y conserva texto vacío, coherente con 02-08. |
| Reset | Conserva solo `system` y devuelve todas las estadísticas a cero/`None`. |

Los datos `CompletionUsage` falsos deben incluir `prompt_tokens`, `completion_tokens` y `total_tokens`. No se inventan precios del proveedor dentro de las pruebas: las tarifas sintéticas se pasan como `Decimal` al fixture.

## Riesgos y decisiones

- No usar `len(history) // 2` para turnos: los mensajes de sistema, resets, contenido vacío y futuras herramientas invalidan esa inferencia.
- No usar `float`: la precisión monetaria pertenece a `Decimal` y al estimador existente.
- No imprimir estadísticas desde el dominio: 02-10 decide el formato de presentación.
- `max_tokens` sigue deprecado por el SDK en favor de `max_completion_tokens`; esta guía no cambia el parámetro sin una migración verificada.

## Checklist de aceptación

- [ ] `ChatTurn` separa texto y uso de proveedor.
- [ ] `SessionStats` representa acumulados de una sola sesión.
- [ ] La acumulación ocurre solo tras completación exitosa.
- [ ] Faltan tarifas → costo `None`, no un precio inventado.
- [ ] Se reutiliza `estimate_cost_usd` con `Decimal`.
- [ ] Existe reset público que conserva el mensaje `system`.
- [ ] Pruebas offline cubren éxito, tarifas ausentes, error, vacío y reset.
- [ ] Ruff, mypy y pytest pasan antes de empezar 02-10.

## Comandos previstos

```bash
uv run ruff format --check .
uv run ruff check src tests
uv run mypy src tests
uv run pytest tests/test_chatbot_cli.py -q
uv run pytest -q
```

## Siguiente paso

Implementar este contrato mediante TDD. Una vez verificado, [02-10-cli-chatbot-loop-and-integration.md](./02-10-cli-chatbot-loop-and-integration.md) conectará las APIs públicas del chatbot con una terminal interactiva.

## Referencias oficiales

- Groq Python SDK y tipos: https://github.com/groq/groq-python
- Chat completions de Groq: https://console.groq.com/docs/chat
