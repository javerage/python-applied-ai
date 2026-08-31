# Manejo tipado y testeable de errores de la API de Groq

> **Aviso de derechos y privacidad:** Este documento es una nota de estudio independiente que resume objetivos de aprendizaje y decisiones de implementación ya verificadas. No reproduce transcripciones de cursos de pago ni material con derechos de autor. No incluye claves de API reales, datos personales ni activos de video. No contiene URLs de medios (p. ej. Wistia) ni tokens con aspecto de `gsk_`. Los fragmentos de prueba usan el marcador `SENSITIVE_PROVIDER_DETAIL` para representar el detalle crudo del proveedor que **nunca** debe imprimirse.

## Estado

**Completed — etapa 5 de 9.** Parte de los 8 tests de 02-05 y añade 6 casos offline para errores tipados, atomicidad y mensajes seguros. El checkpoint acumulado queda en **14 tests**. No se provocan errores mediante llamadas reales.

## Objetivo de aprendizaje

Convertir la primera llamada a la API en una unidad tipada y testeable (`call_ai`) que delega la presentación y la salida al límite de la línea de comandos (`main`), captura las excepciones específicas del SDK de Groq (y un `GroqError` final) sin `except Exception` desnudo, y se prueba offline con un cliente falso inyectado.

## Ruta rápida

1. (Hecho) [02-04-first-groq-api-call.md](./02-04-first-groq-api-call.md) — `config.py` y `hello_ai.py` funcionando.
2. (Hecho) [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) (`cost.py` + `tests/test_cost.py`) completo y sincronizado.
3. (Hecho) Refactor de `hello_ai.py`: `call_ai(client, question, settings) -> ChatCompletion` devuelve la respuesta completa; `main` captura excepciones y presenta mensajes amigables.
4. (Hecho) `tests/test_hello_ai.py` fuerza fallos de auth/rate-limit/not-found/connection con un cliente falso (`MagicMock`) y helpers seguros de excepciones.
5. (Hecho) Verificado con `ruff format --check .`, `ruff check .`, `mypy src tests --strict` y `pytest` (offline).

## Resumen del concepto y mapeo OpenAI → Groq

La lección original de manejo de errores de la API enseña a capturar los errores del SDK del proveedor y a dar mensajes útiles. El SDK de Groq replica la jerarquía de excepciones de OpenAI, por lo que el mapeo es directo. No se reproduce el texto ni el material de video del curso.

| Concepto original (OpenAI) | Adaptación Groq (verificada) |
| --- | --- |
| Capturar excepciones del SDK `openai` | Capturar `AuthenticationError`, `RateLimitError`, `NotFoundError`, `APIConnectionError` y, al final, `GroqError` (subclases de `GroqError`) |
| Imprimir / `sys.exit` / `raise` dentro de la función de dominio | `call_ai` solo llama a la API y devuelve/propaga; `main` presenta y decide la salida |
| `except Exception` desnudo como red de seguridad | Capturar excepciones específicas y, al final, `GroqError` (no `Exception`) |
| "Probar" fallos sobrescribiendo `.env` o desactivando el Wi-Fi | Probar con un cliente falso inyectado (`MagicMock`) cuyo `.chat.completions.create` lanza la excepción |
| Reintento manual en bucle ante fallo | El SDK reintenta con backoff según `max_retries` (por defecto 2); no se añade bucle manual |

## Patrones de riesgo y corrección

| Patrón | Riesgo / por qué | Correcto en Groq (verificado) |
| --- | --- | --- |
| `except Exception` desnudo | Oculta bugs de programación (`ValueError`, `TypeError`) y es un parche, no manejo de errores | `AuthenticationError` → `RateLimitError` → `NotFoundError` → `APIConnectionError` → `GroqError` |
| Imprimir o `SystemExit` dentro de `call_ai` | Acopla la lógica de dominio a la presentación; imposibilita las pruebas | `call_ai` solo llama a la API y devuelve `ChatCompletion`; `main` imprime y retorna |
| Sobrescribir `.env` para simular fallo | Corrompe la configuración real y es destructivo | Inyectar un cliente falso que lanza la excepción |
| Desactivar el Wi-Fi para simular fallo | Acción manual, no automatizable ni aislada | Efecto lateral (`side_effect`) en el cliente falso |
| Llamada real a la API en las pruebas | Consume cuota y red; no es repetible | Pruebas puras offline con `MagicMock`, sin red ni cuota |
| Bucle manual de reintentos | Compite con el reintento nativo del SDK y puede duplicar tráfico | Dejar que el SDK reintente (`max_retries` por defecto) |
| Imprimir `f"...{exc}"` del proveedor | Fuga de detalles internos del proveedor (posible secreto) | Mensaje genérico fijo; los detalles crudos no se imprimen |
| `GroqError()` sin argumentos | `GroqError` **puede** llevar un mensaje; afirmar que no recibe args es falso | `GroqError("detalle")` es válido; el límite lo oculta tras un mensaje fijo |

## Decisión de arquitectura

Se mantiene **un solo módulo** `hello_ai.py` y se añade una función de dominio tipada:

```python
def call_ai(client: Groq, question: str, settings: Settings) -> ChatCompletion: ...
```

- **`call_ai(client, question, settings) -> ChatCompletion`**: recibe el cliente **inyectado** (tipado `Groq`), la pregunta y la configuración; devuelve la respuesta completa `ChatCompletion`. Así `report_usage(response, settings)` y la estimación de costo de `cost.py` siguen siendo reutilizables sobre el MISMO `response`.
- **El cliente se inyecta** para que las pruebas pasen un `MagicMock` en vez del cliente real, sin red ni cuota.
- **No se crea un segundo archivo**: se conserva el alcance de principiante de una sola lección.

## Regla de límite (boundary)

- **La función de dominio no imprime ni llama a `SystemExit`.** Solo invoca la API y devuelve la respuesta (o deja propagar la excepción tipada de Groq).
- **`main` es el límite de presentación y salida**: captura las excepciones específicas y, al final, `GroqError`, y las mapea a mensajes amigables y a un `return`, sin `raise` ni `SystemExit` en la capa de dominio.

## Nota técnica: jerarquía de captura

- **Especifico→genérico:** los `except` van del más específico al más genérico. `AuthenticationError`, `RateLimitError`, `NotFoundError` (subclases de `APIStatusError`) van primero; luego `APIConnectionError`; finalmente `GroqError`. Si se invierte el orden, los genéricos capturan antes de llegar a los específicos.
- **`APIConnectionError` vs `APIStatusError`:** `APIConnectionError` se lanza cuando no hay respuesta HTTP del proveedor (red caída, timeout) y su constructor recibe `message=` y `request=` separados. `APIStatusError` cubre respuestas con código de estado HTTP (4xx/5xx) — subclase de la que heredan `AuthenticationError`, `RateLimitError` y `NotFoundError` — y su constructor requiere `(message, *, response, body)` con un `httpx.Response` adjunto.
- **Secretos:** los mensajes de usuario no deben incluir el detalle crudo de la excepción del proveedor (`f"...{exc}"`), porque puede contener tokens internos, IDs de respuesta o metadatos sensibles. Se usa un mensaje fijo genérico y el valor `SENSITIVE_PROVIDER_DETAIL` solo como marcador de prueba.
- **Reintentos:** no hay política de retry implementada; se confía en el reintento nativo del SDK (`max_retries` por defecto). No se añade bucle manual ni lógica de backoff propia.

## Prohibiciones explícitas (verificadas como ausentes)

- No `except Exception` desnudo (se usa `GroqError` como último recurso tipado).
- No edición destructiva de `.env` para "provocar" fallos en pruebas.
- No desactivar el Wi-Fi para simular errores de conexión.
- No llamadas reales a la API dentro de las pruebas (cero cuota, cero red).
- No bucle manual de reintentos (reintento nativo del SDK).
- No `print(f"...{exc}")` del detalle crudo del proveedor.

## Reintentos nativos del SDK

El SDK de Groq reintenta con retroceso exponencial según `max_retries` (por defecto 2) para errores reintentables. Por tanto: no se añade ningún bucle manual de reintentos; `call_ai` simplemente deja que la excepción final se propague y `main` la presenta.

## Fragmentos verificados (ingleses, en verde con ruff/mypy/pytest)

> Estos fragmentos coinciden con el código y las pruebas actuales. No son un plan: están implementados y verificados offline.

### `hello_ai.py` — `call_ai` (dominio tipado, sin print/SystemExit/try)

```python
from groq import Groq
from groq.types.chat import ChatCompletion

from python_applied_ai.config import Settings


def call_ai(
    client: Groq,
    question: str,
    settings: Settings,
) -> ChatCompletion:
    """Call Groq and return the complete chat response."""

    return client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": question}],
        max_tokens=settings.llm_max_tokens,
        temperature=0.7,
        top_p=0.9,
    )
```

### `hello_ai.py` — `main` (límite de presentación/salida: específicas → `GroqError`)

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


def main() -> None:
    """Print a greeting from the LLM."""
    settings = get_settings()

    if not settings.groq_api_key or not settings.groq_api_key.get_secret_value():
        print("Missing GROQ API KEY. Add it to .env and retry.")
        return

    client = Groq(api_key=settings.groq_api_key.get_secret_value())

    try:
        response = call_ai(
            client,
            "Say hello in three languages: Spanish, English, and French.",
            settings,
        )
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
    except GroqError:
        print("Unexpected Groq error. Try again later or check the Groq status page.")
        return

    content = response.choices[0].message.content
    print(content if content is not None else "The model returned an empty response.")
    report_usage(response, settings)
```

> Nota: `call_ai` y `report_usage` se definen más arriba en el mismo módulo `hello_ai.py`; se invocan directamente y **no** deben importarse del módulo hacia sí mismo.

- `main` llama a `call_ai` **exactamente una vez**, conserva el prompt, imprime `content` y luego llama a `report_usage(response, settings)` sobre la MISMA `response`.
- Orden de manejo: `AuthenticationError` → `RateLimitError` → `NotFoundError` → `APIConnectionError` → `GroqError`.
- El manejador genérico es **exactamente** `except GroqError: print("Unexpected Groq error. Try again later or check the Groq status page."); return`. El detalle crudo del proveedor no se imprime.

## Pruebas offline seguras (MagicMock + helpers de excepciones)

Las pruebas fuerzan cada fallo mediante un cliente falso cuyo `.chat.completions.create` tiene un `side_effect` que lanza la excepción. **Verificado contra el paquete `groq` instalado:** las subclases `APIStatusError` (`AuthenticationError`, `RateLimitError`, `NotFoundError`) requieren `(message, *, response, body)` donde `response` es un `httpx.Response` con un `request` adjunto en memoria; `APIConnectionError` requiere `message=` y `request=` por separado. `GroqError` acepta un mensaje (`GroqError("detalle")`).

### Helpers de excepciones (tests)

```python
import httpx
from groq import (
    APIConnectionError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)


def _fake_request() -> httpx.Request:
    """Create an in-memory HTTP request without network access."""
    return httpx.Request("POST", "https://api.groq.com/v1/chat/completions")


def _connection_error() -> APIConnectionError:
    # APIConnectionError needs message= + request= (no httpx.Response).
    return APIConnectionError(message="Connection failed", request=_fake_request())


def _auth_error() -> AuthenticationError:
    # Status errors need (message, *, response, body); attach an in-memory request.
    return AuthenticationError(
        "SENSITIVE_PROVIDER_DETAIL",
        response=httpx.Response(401, request=_fake_request()),
        body=None,
    )


def _rate_limit_error() -> RateLimitError:
    return RateLimitError(
        "SENSITIVE_PROVIDER_DETAIL",
        response=httpx.Response(429, request=_fake_request()),
        body=None,
    )


def _not_found_error() -> NotFoundError:
    return NotFoundError(
        "SENSITIVE_PROVIDER_DETAIL",
        response=httpx.Response(404, request=_fake_request()),
        body=None,
    )
```

### Helper de `Settings` (solo tests) y su tradeoff

```python
from typing import cast
from pydantic import SecretStr
from python_applied_ai.config import Settings


def _test_settings(
    *,
    groq_api_key: SecretStr | None = None,
    llm_model: str = "openai/gpt-oss-20b",
    llm_max_tokens: int = 256,
) -> Settings:
    """Build trusted test settings without reading environment sources."""
    return Settings.model_construct(
        groq_api_key=groq_api_key,
        llm_model=llm_model,
        llm_max_tokens=llm_max_tokens,
    )
```

- `Settings.model_construct(...)` omite la validación y la carga de entorno, por lo que las pruebas no tocan `.env` ni red.
- **Tradeoff:** solo es aceptable para fixtures de confianza dentro de `tests/`. Nunca debe moverse a `src/`, donde la validación real de entorno es obligatoria.

## Por qué existen estas pruebas (honestidad de TDD)

- **`test_call_ai_propagates_connection_error` (propagación):** nació en fase RED para exigir que `call_ai` no capture ni silencie errores tipados; confirma que la excepción llega al límite.
- **`test_main_handles_unexpected_groq_error_safely` (fallback genérico):** también de RED; verifica que el mensaje genérico se muestra y que `SENSITIVE_PROVIDER_DETAIL` **no** aparece en la salida (privacidad).
- **`test_main_handles_specific_groq_errors_safely` (4 casos parametrizados):** son pruebas de caracterización; se esperan en verde porque el comportamiento de los manejadores específicos ya existía. Documentan el mapeo mensaje por mensaje.

### `tests/test_hello_ai.py` — propagación (pytest.raises)

```python
from unittest.mock import MagicMock
import pytest
from groq import APIConnectionError, Groq
from python_applied_ai.hello_ai import call_ai


def test_call_ai_propagates_connection_error() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = _connection_error()
    fake_client = cast(Groq, mock_client)

    settings = _test_settings()

    with pytest.raises(APIConnectionError):
        call_ai(fake_client, "Hi", settings)
```

### `tests/test_hello_ai.py` — fallback genérico (privacidad)

```python
def test_main_handles_unexpected_groq_error_safely(
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _test_settings(groq_api_key=SecretStr("test-key"))
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = GroqError("SENSITIVE_PROVIDER_DETAIL")

    with (
        patch("python_applied_ai.hello_ai.get_settings", return_value=settings),
        patch("python_applied_ai.hello_ai.Groq", return_value=fake_client),
    ):
        main()

    captured = capsys.readouterr()
    assert "unexpected groq" in captured.out.lower()
    assert "SENSITIVE_PROVIDER_DETAIL" not in captured.out
```

### `tests/test_hello_ai.py` — caracterización parametrizada (4 ramas)

```python
@pytest.mark.parametrize(
    ("make_error", "expected_fragment"),
    [
        (_auth_error, "authentication failed"),
        (_rate_limit_error, "rate limit"),
        (_not_found_error, "model not found"),
        (_connection_error, "connection error"),
    ],
)
def test_main_handles_specific_groq_errors_safely(
    capsys: pytest.CaptureFixture[str],
    make_error: Callable[[], GroqError],
    expected_fragment: str,
) -> None:
    settings = _test_settings(groq_api_key=SecretStr("test-key"))
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = make_error()

    with (
        patch("python_applied_ai.hello_ai.get_settings", return_value=settings),
        patch("python_applied_ai.hello_ai.Groq", return_value=fake_client),
    ):
        main()

    captured = capsys.readouterr()
    assert expected_fragment in captured.out.lower()
    assert "SENSITIVE_PROVIDER_DETAIL" not in captured.out
```

Total del archivo: **6 casos** (1 propagación + 1 genérico + 4 parametrizados). Checkpoint acumulado: **14 tests**.

## `temperature` y `top_p`

El código usa `temperature=0.7` y `top_p=0.9`, ambos válidos para `openai/gpt-oss-20b` (Groq documenta `temperature` 0.0–2.0 y `top_p` 0.0–1.0). Recomendaciones:

- Ajuste **uno a la vez** para aislar efectos (guía oficial de muestreo).
- `temperature=0` hace la salida "más determinista", **no** "idéntica garantizada"; la reproducibilidad real requiere `seed` y parámetros/modelo idénticos.
- El experimento profundo de `temperature` queda para [02-07-temperature-and-reproducibility.md](./02-07-temperature-and-reproducibility.md).

## Evidencia de verificación (offline, sin llamadas reales)

| Comando | Resultado |
| --- | --- |
| `uv run ruff format --check .` | limpio |
| `uv run ruff check .` | All checks passed |
| `uv run mypy src tests --strict` | Success: no issues found |
| `uv run pytest tests/test_hello_ai.py -q` | 6 passed |
| `uv run pytest -q` | 14 passed en este checkpoint |

No se realizaron llamadas reales a la API para validar el manejo de errores (cero cuota, cero red).

## Checklist de aceptación

- [x] `call_ai(client, question, settings) -> ChatCompletion` está tipada y devuelve la respuesta completa.
- [x] El cliente se inyecta (las pruebas pasan un falso).
- [x] La función de dominio no imprime ni llama a `SystemExit`; no tiene `try/except` interno.
- [x] `main` captura `AuthenticationError`, `RateLimitError`, `NotFoundError`, `APIConnectionError` y, al final, `GroqError`.
- [x] No hay `except Exception` desnudo.
- [x] No se editó `.env` de forma destructiva ni se desactivó el Wi-Fi para probar.
- [x] No hay llamadas reales a la API en las pruebas (cero cuota, cero red).
- [x] No hay bucle manual de reintentos (reintento nativo del SDK).
- [x] Las pruebas usan `MagicMock` con `side_effect` y helpers seguros de excepciones (request adjunto para errores de estado; `message=`+`request=` para conexión).
- [x] El manejador genérico es el mensaje fijo y no imprime detalles crudos del proveedor.
- [x] `Settings.model_construct` solo en `tests/`, nunca en `src/`.
- [x] Ruff, mypy y **14 tests acumulados** en verde.
- [x] [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) completo y sincronizado (prerrequisito cumplido).

## Comandos

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests --strict
uv run pytest tests/test_hello_ai.py -q
uv run pytest -q
```

## Resultado de etapa y siguiente paso

`call_ai` queda separado del límite de presentación; los errores específicos se traducen a mensajes seguros y los **14 tests acumulados** están verdes. Continúe con [02-07-temperature-and-reproducibility.md](./02-07-temperature-and-reproducibility.md) para convertir el muestreo en configuración validada.

## Mensaje de commit sugerido

Para la implementación de la refactorización:

```text
refactor: add typed call_ai and Groq error handling at CLI boundary
```

Para este documento (estado verificado):

```text
docs: mark 02-06 Groq error handling as implemented and verified offline
```

## Referencias externas oficiales

- groq-python: https://github.com/groq/groq-python
- Documentación de Groq: https://console.groq.com/docs/quickstart
- Límites de tasa: https://console.groq.com/docs/rate-limits
- Modelos: https://console.groq.com/docs/models
- Modelo: https://console.groq.com/docs/model/openai/gpt-oss-20b
