# Manejo tipado y testeable de errores de la API de Groq

> **Aviso de derechos y privacidad:** Este documento es una nota de estudio independiente que resume objetivos de aprendizaje y decisiones originales de implementación. No reproduce transcripciones de cursos de pago ni material con derechos de autor. No incluye claves de API reales, datos personales ni activos de video. No contiene URLs de medios (p. ej. Wistia) ni tokens con aspecto de `gsk_`.

## Estado

**Planned** — lección de la sección 2 secuenciada **después** del paso opcional de costo de [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md). El código aquí descrito es un **plan**: no está implementado, no se ha ejecutado `ruff`/`mypy`/`pytest` sobre él, y no debe marcarse como terminado. Solo se verificaron las firmas de los constructores de excepciones contra el paquete `groq` instalado (v1.7.0).

## Objetivo de aprendizaje

Convertir la función de dominio de la primera llamada en una unidad tipada y testeable que delega la presentación y la salida al límite de la línea de comandos (`main`), captura las excepciones específicas del SDK de Groq (y un `GroqError` final) sin usar `except Exception` desnudo, y se prueba de forma offline con un cliente falso inyectado.

## Ruta rápida

1. (Hecho) Completar [02-04-first-groq-api-call.md](./02-04-first-groq-api-call.md) — `config.py` y `hello_ai.py` funcionando.
2. (Pendiente) Completar la fase opcional de costo de [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) (`cost.py` + `tests/test_cost.py`) antes de esta lección.
3. (Planned) Refactorizar `hello_ai.py`: añadir `call_ai(client, question, settings) -> ChatCompletion` que devuelve la respuesta completa; `main` captura excepciones y presenta mensajes amigables.
4. (Planned) Añadir `tests/` que fuerzan fallos de auth/rate-limit/not-found/connection con un cliente falso (`MagicMock`) y un helper seguro de excepciones.
5. (Planned) Verificar con `ruff format .`, `ruff check .`, `mypy src` (strict) y `pytest`.

## Resumen del concepto del instructor y mapeo OpenAI → Groq

La lección original de manejo de errores de la API enseña a capturar los errores del SDK del proveedor y a dar mensajes útiles. Esta nota conserva ese objetivo y lo adapta a Groq; el SDK de Groq replica la jerarquía de excepciones de OpenAI, por lo que el mapeo es directo. No se reproduce el texto ni el material de video del curso.

| Concepto del instructor (OpenAI) | Adaptación Groq |
| --- | --- |
| Capturar excepciones del SDK `openai` | Capturar excepciones de `groq` (mismas clases; subclases de `GroqError`) |
| Imprimir / `sys.exit` / `raise` dentro de la función de dominio | La función de dominio solo llama a la API y devuelve/propaga; `main` presenta y decide la salida |
| `except Exception` desnudo como red de seguridad | Capturar excepciones específicas y, al final, `GroqError` (no `Exception`) |
| "Probar" fallos sobrescribiendo `.env` o desactivando el Wi-Fi | Probar con un cliente falso inyectado (`MagicMock`) cuyo `.chat.completions.create` lanza la excepción |
| Reintento manual en bucle ante fallo | El SDK reintenta `RateLimitError`/`APIConnectionError` con backoff hasta `max_retries=2`; no añadir bucle manual |

## Conceptos correctos y patrones de riesgo

| Patrón | Riesgo / por qué | Correcto en Groq |
| --- | --- | --- |
| `except Exception` desnudo | Oculta bugs de programación (`ValueError`, `TypeError`) y es un parche, no manejo de errores | Capturar `AuthenticationError`, `RateLimitError`, `NotFoundError`, `APIConnectionError` y, al final, `GroqError` |
| Imprimir o `SystemExit` dentro de `call_ai` | Acopla la lógica de dominio a la presentación; imposibilita las pruebas | `call_ai` solo llama a la API y devuelve `ChatCompletion`; `main` imprime y retorna |
| Sobrescribir `.env` para simular fallo | Corrompe la configuración real y es destructivo | Inyectar un cliente falso que lanza la excepción |
| Desactivar el Wi-Fi para simular fallo | Acción manual, no automatizable ni aislada | Efecto lateral (`side_effect`) en el cliente falso |
| Llamada real a la API en las pruebas | Consume cuota y red; no es repetible | Pruebas puras offline con `MagicMock`, sin red ni cuota |
| Bucle manual de reintentos | Compite con el reintento nativo del SDK y puede duplicar tráfico | Dejar que el SDK reintente (`max_retries=2` por defecto) |
| `temperature=0` como "idéntico garantizado" | La salida puede variar según el snapshot del modelo; solo es "más determinista" | Documentar que `temperature=0` es más determinista, no idéntico |

## Decisión de arquitectura

Mantener **un solo módulo** `hello_ai.py` (sin duplicar en un `hello_error_managment.py` con falta de ortografía) y añadir una función de dominio tipada:

```python
def call_ai(client: Groq, question: str, settings: Settings) -> ChatCompletion: ...
```

- **`call_ai(client, question, settings) -> ChatCompletion`**: recibe el cliente **inyectado** (tipado `Groq`), la pregunta y la configuración; devuelve la respuesta completa `ChatCompletion`. Así `report_usage(response)` y la estimación de costo de `cost.py` siguen siendo reutilizables sobre el MISMO `response`.
- **El cliente se inyecta** para que las pruebas pasen un `MagicMock` en vez del cliente real, sin red ni cuota.
- **No se crea un segundo archivo**: se conserva el alcance de principiante de una sola lección.

## Regla de límite (boundary)

- **La función de dominio no imprime ni llama a `SystemExit`.** Solo invoca la API y devuelve la respuesta (o deja propagar la excepción tipada de Groq).
- **`main` es el límite de presentación y salida**: captura las excepciones específicas y, al final, `GroqError`, y las mapea a mensajes amigables y a un `return` (comportamiento de salida), sin `raise` ni `SystemExit` en la capa de dominio.

## Prohibiciones explícitas

- No usar `except Exception` desnudo (usar `GroqError` como último recurso tipado).
- No editar `.env` de forma destructiva para "provocar" fallos en pruebas.
- No desactivar el Wi-Fi para simular errores de conexión.
- No realizar llamadas reales a la API dentro de las pruebas (cero cuota, cero red).
- No añadir un bucle manual de reintentos.

## Reintentos nativos del SDK

El SDK de Groq reintenta `RateLimitError` y `APIConnectionError` con retroceso exponencial hasta `max_retries=2` por defecto. Por tanto: no se añade ningún bucle manual de reintentos; `call_ai` simplemente deja que la excepción final se propague y `main` la presenta. El `hello_ai.py` actual ya indica correctamente "do not loop".

## Plan de pruebas offline seguro (MagicMock + helper de excepciones)

Las pruebas fuerzan cada fallo mediante un cliente falso cuyo `.chat.completions.create` tiene un `side_effect` que lanza la excepción correspondiente. **Importante (verificado contra `groq` 1.7.0 instalado):** `GroqError` se construye sin argumentos (`GroqError()`), pero sus subclases `APIError`/`APIStatusError` (`AuthenticationError`, `RateLimitError`, `NotFoundError`, `APIConnectionError`) requieren objetos reales `httpx.Request`/`httpx.Response` en el constructor — **no** aceptan un simple mensaje de texto. Por eso el helper seguro construye esos objetos en memoria (sin red) en lugar de inventar constructores inválidos.

```python
import httpx

from groq import (
    APIConnectionError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)


def _fake_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.groq.com/v1/chat/completions")


def auth_error() -> AuthenticationError:
    # APIStatusError necesita (message, *, response, body); httpx.Response es en memoria, sin red.
    return AuthenticationError("invalid API key", response=httpx.Response(401), body=None)


def rate_limit_error() -> RateLimitError:
    return RateLimitError("rate limit reached", response=httpx.Response(429), body=None)


def not_found_error() -> NotFoundError:
    return NotFoundError("model not found", response=httpx.Response(404), body=None)


def connection_error() -> APIConnectionError:
    # APIConnectionError necesita (message=..., request=...); httpx.Request es en memoria, sin red.
    return APIConnectionError(message="connection failed", request=_fake_request())
```

Una prueba (AAA, sin red) inyecta un `MagicMock` y verifica que `main`/`call_ai` maneja la excepción:

```python
from unittest.mock import MagicMock

from python_applied_ai.hello_ai import call_ai


def test_call_ai_propagates_auth_error() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = auth_error()

    settings = MagicMock()
    settings.llm_model = "openai/gpt-oss-20b"
    settings.llm_max_tokens = 256

    raised = False
    try:
        call_ai(fake_client, "hi", settings)
    except AuthenticationError:
        raised = True
    assert raised is True
```

Casos cubiertos: autenticación (`AuthenticationError`), límite de tasa (`RateLimitError`), modelo no encontrado (`NotFoundError`), y conexión (`APIConnectionError`). Todas las pruebas son puras y offline; ninguna toca `.env`, la red ni la cuota.

## `temperature` y `top_p`

El código actual usa `temperature=0.7` y `top_p=0.9`, ambos **válidos** para `openai/gpt-oss-20b` (Groq documenta `temperature` 0.0–2.0 y `top_p` 0.0–1.0). Recomendaciones:

- Ajuste **uno a la vez** para aislar efectos (guía oficial de muestreo).
- `temperature=0` hace la salida "más determinista", **no** "idéntica garantizada"; la reproducibilidad real requiere una semilla (`seed`) y parámetros/modelo idénticos.
- El ejercicio profundo de `temperature` queda para una lección posterior; aquí solo se conservan los valores actuales.

## Fragmentos planificados (inglés, no verificados por ruff/mypy/pytest)

> Estos fragmentos son el **plan** de la refactorización. No afirman código existente ni pruebas en verde. Las firmas de excepciones fueron verificadas contra `groq` 1.7.0; el resto debe pasar `ruff`/`mypy --strict`/`pytest` al implementarse.

`hello_ai.py` — función de dominio tipada (devuelve la respuesta completa):

```python
from groq import Groq
from groq.types.chat import ChatCompletion

from python_applied_ai.config import Settings


def call_ai(client: Groq, question: str, settings: Settings) -> ChatCompletion:
    """Call the Groq chat completions API and return the full response.

    The domain function does NOT print or call SystemExit; it returns the
    full ChatCompletion so report_usage/cost remain reusable, and lets Groq
    exceptions propagate to the CLI boundary (main).
    """
    return client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": question}],
        max_tokens=settings.llm_max_tokens,
        temperature=0.7,
        top_p=0.9,
    )
```

`hello_ai.py` — `main` como límite de presentación/salida (captura específicas + `GroqError`):

```python
from groq import (
    APIConnectionError,
    AuthenticationError,
    Groq,
    GroqError,
    NotFoundError,
    RateLimitError,
)

from python_applied_ai.config import get_settings
from python_applied_ai.hello_ai import call_ai, report_usage


def main() -> None:
    settings = get_settings()
    if not settings.groq_api_key or not settings.groq_api_key.get_secret_value():
        print("Missing GROQ API KEY. Add it to .env and retry.")
        return

    client = Groq(api_key=settings.groq_api_key.get_secret_value())
    try:
        response = call_ai(client, "Say hello in three languages.", settings)
    except AuthenticationError:
        print("Authentication failed: GROQ_API_KEY is invalid or revoked.")
        return
    except RateLimitError:
        print("Rate limit reached. Wait and retry later; do not loop.")
        return
    except NotFoundError:
        print(f"Model not found: {settings.llm_model}. Check LLM_MODEL in .env.")
        return
    except APIConnectionError:
        print("Connection error: check your network and retry.")
        return
    except GroqError as exc:
        print(f"Groq API error: {exc}")
        return

    report_usage(response)
```

## Checklist de aceptación

- [ ] `call_ai(client, question, settings) -> ChatCompletion` está tipada y devuelve la respuesta completa.
- [ ] El cliente se inyecta (las pruebas pasan un falso).
- [ ] La función de dominio no imprime ni llama a `SystemExit`.
- [ ] `main` captura `AuthenticationError`, `RateLimitError`, `NotFoundError`, `APIConnectionError` y, al final, `GroqError`.
- [ ] No hay `except Exception` desnudo.
- [ ] No se editó `.env` de forma destructiva ni se desactivó el Wi-Fi para probar.
- [ ] No hay llamadas reales a la API en las pruebas (cero cuota, cero red).
- [ ] No hay bucle manual de reintentos (se usa el reintento nativo del SDK).
- [ ] Las pruebas usan `MagicMock` con `side_effect` y el helper seguro de excepciones.
- [ ] `uv run ruff format .`, `ruff check .`, `uv run mypy src` (strict) y `uv run pytest` en verde (al implementar).
- [ ] El paso opcional de costo de [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) está completo antes de esta lección.

## Comandos

```bash
uv run pytest
uv run ruff format .
uv run ruff check .
uv run mypy src
```

## Estado actual

- Lección **Planned**; no implementada.
- La fase opcional de costo de [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) sigue pendiente y debe completarse primero (secuencia: costo → errores).
- Se verificaron solo las firmas de los constructores de excepciones de `groq` 1.7.0; el código de esta lección no se ha ejecutado.

## Mensaje de commit sugerido

Para este documento (planeación):

```text
docs: plan Groq API error handling with typed call_ai and safe offline tests
```

Para la futura implementación de la refactorización (no en este paso):

```text
refactor: add typed call_ai and Groq error handling at CLI boundary
```

No se realiza commit ni push en este paso; queda a decisión del usuario.

## Referencias externas oficiales

- groq-python: https://github.com/groq/groq-python
- Documentación de Groq: https://console.groq.com/docs/quickstart
- Límites de tasa: https://console.groq.com/docs/rate-limits
- Modelos: https://console.groq.com/docs/models
- Modelo: https://console.groq.com/docs/model/openai/gpt-oss-20b
