# Chatbot en CLI con historial de conversación (Parte 1)

> **Aviso de privacidad y procedencia:** Esta guía es un documento de estudio **autónomo y original**. No reproduce la transcripción de ningún curso de pago ni el código de terceros. No incluye identificadores de cuentas/proyectos, URLs de medios (p. ej. Wistia), metadatos de respuesta, marcas de tiempo, nombres de archivo, claves de API, identificadores de respuesta, tarifas privadas, rutas personales ni nombres de host. Los fragmentos reflejan la implementación verificada; no se realizó una llamada real a la API para esta lección.
>
> **Fuente externa de arranque (OpenAI), no copiar:** se usa un Gist público de OpenAI solo como punto de partida conceptual (enlace **volátil**, citado una vez en Referencias externas oficiales; puede cambiar o desaparecer). Esta guía es **autónoma y original**: no reproduce ese Gist ni el material del curso de pago.

## Estado

**Completed — etapa 7 de 9.** Parte del checkpoint de 46 tests de 02-07 y crea el dominio `ChatBot` con historial transaccional. Añade 5 pruebas offline y deja **51 tests acumulados**. Prerrequisitos:

- [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) Completed.
- [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md) Completed e implementado (define `call_ai`, el límite de errores y el patrón de cliente inyectado).
- [02-07-temperature-and-reproducibility.md](./02-07-temperature-and-reproducibility.md) Completed; validación y experimento controlado implementados offline.

La etapa introduce 5 pruebas T1–T5 en `tests/test_chatbot_cli.py`; todas son offline. Las 25 pruebas posteriores del mismo archivo pertenecen a 02-09/02-10 y no forman parte de este checkpoint.

## Roadmap del proyecto (tres videos)

El proyecto de chatbot CLI se construye en tres incrementos consecutivos:

| Guía | Video | Título de trabajo | Contenido exacto |
| --- | --- | --- | --- |
| 02-08 (esta) | Video 1 | Clase de dominio con historial | Se implementa ahora |
| 02-09 | Video 2 | Uso, costo teórico y estadísticas de sesión | Siguiente incremento |
| 02-10 | Video 3 | Bucle CLI e integración final | Cierre del producto |

> **Límite de alcance:** esta guía no crea estadísticas acumuladas, comandos de terminal ni entrypoint final. Esas responsabilidades se añaden en 02-09 y 02-10.

## Ruta rápida (primero el resultado)

1. (Hecho) [02-06-groq-api-error-handling.md](./02-06-groq-api-error-handling.md) — cliente inyectado y manejo de errores.
2. (Hecho) [02-07-temperature-and-reproducibility.md](./02-07-temperature-and-reproducibility.md) — Completed.
3. **(Hecho) Esta Parte 1:** crear la clase de dominio `ChatBot` con `history` tipado y `chat()` transaccional.
4. **(Siguiente, 02-09):** extender el resultado con uso y estadísticas de sesión.
5. **(Cierre, 02-10):** integrar el bucle CLI, comandos y entrypoint.

**Resultado de esta lección:** un objeto `ChatBot` que recuerda la conversación (system + user + assistant) y la reenvía en cada turno, con errores de Groq que se propagan al límite, igual que en 02-06.

## Límite explícito de la lección

| Esta Parte 1 (se crea) | Se difiere deliberadamente |
| --- | --- |
| Clase de dominio `ChatBot` | Bucle interactivo de lectura/escritura (02-10) |
| `history: list[ChatCompletionMessageParam]` | Presentación y comandos (02-10) |
| `chat(user_message) -> str` | `ChatTurn`, tokens y costo acumulado (02-09) |
| Inyección del cliente Groq y `Settings` | Persistencia en disco / RAG (por confirmar) |

No implemente el bucle de CLI ni el banner en esta lección: mantenga el alcance en la clase de dominio para poder probarla 100% offline.

## Objetivos de aprendizaje

- Construir **mensajes de conversación tipados** (`system`, `user`, `assistant`) con TypedDicts del SDK.
- Distinguir los **roles** y por qué el `system` se envía en cada turno.
- **Inyectar** el cliente Groq (tipado `Groq`) para poder probar sin red ni cuota.
- Mantener **memoria de sesión** mediante una lista de historial.
- Garantizar un historial **transaccional**: solo se confirma tras una respuesta exitosa.
- Aplicar **TDD offline** (AAA) con `MagicMock`/`cast`, cero red/cuota.
- Entender el **costo de crecimiento de contexto** (tokens, latencia, costo).

## Mapeo: Gist/OpenAI → arquitectura Groq neutral

El Gist de arranque usa OpenAI con valores hardcodeados. Esta guía lo reescribe con Groq y diseño provider-neutral. **No se copia su código.**

| En el Gist (OpenAI, hardcodeado) | En esta guía (Groq, neutral) |
| --- | --- |
| Cliente `OpenAI(api_key=...)` global | Cliente **`Groq` inyectado** en `ChatBot.__init__(client: Groq, ...)` |
| `load_dotenv()` + `os.getenv(...)` | `Settings` (pydantic-settings) vía `get_settings()`; en tests `Settings.model_construct` |
| Modelo como string literal fijo | `settings.llm_model` |
| System prompt en español escrito en el código | Parámetro del constructor `system_prompt: str` (no se copia el texto original) |
| Tarifas `float` hardcodeadas | `Decimal` opcional ya preparado en 02-05; acumulación llega en 02-09 |
| `main`/banner sin tipos | Límite de composición reservado para 02-10 |
| **No existe clase `ChatBot`** | `ChatBot` es aporte de la lección (dominio + historial + `chat`) |

## Advertencia de comparación con la implementación pública final

Existe un repositorio público final del curso (citado una vez en Referencias externas oficiales, rama `section-2-fundamentos`). Es **referencia para comparar después de implementar**, no código a copiar. Su implementación final es **OpenAI-acoplada** y presenta patrones que esta guía evita a propósito:

| En la implementación pública final (OpenAI) | En nuestra adaptación (Groq, neutral) |
| --- | --- |
| Acoplamiento a OpenAI | Cliente `Groq` **inyectado** |
| Efectos de lado de `dotenv`/hardcodeados | `Settings` (pydantic-settings) |
| Modelo hardcodeado + tarifas `float` | `settings.llm_model` + `Decimal` (nunca `float`) |
| Historial **ilimitado** (crece sin cota) | `history` tipado; estrategias de contexto por confirmar |
| `except Exception` amplio | Errores específicos de Groq (como 02-06) |
| Sin pruebas | TDD offline (MagicMock/`cast`, `Settings.model_construct`) |

No copie el acoplamiento OpenAI, los efectos de `dotenv`, valores hardcodeados, historial ilimitado, `Exception` amplio ni ausencia de pruebas. No adelante aquí las responsabilidades de 02-09/02-10.

## Conceptos correctos y correcciones

- **Historial completo = contexto, pero con costo.** Reenviar `system + user + assistant + ...` en cada turno da continuidad conversacional, pero **crece el número de tokens, la latencia y el costo** por llamada. No es "gratis".
- **RAG no es un reemplazo directo de la memoria de chat.** Recuperación aumentada (RAG) aporta conocimiento externo desde documentos; la memoria de chat aporta continuidad del diálogo. Son problemas distintos.
- **Estrategias futuras (posteriores a 02-09), no promesas de esta lección ni de 02-09:** ventanas de contexto, resumen/compresión de historial, persistencia en disco, e integración RAG. Evite afirmar que "RAG por sí solo resuelve toda la historia".
- **No reclame determinismo.** La temperatura (02-07) no garantiza salidas idénticas; el historial solo cambia el contexto enviado.

## Arquitectura implementada y verificada

> Los fragmentos de esta sección reflejan `src/python_applied_ai/chatbot_cli.py`. El dominio no imprime, no captura errores ni crea un bucle CLI.

### Contrato de la clase

```python
# src/python_applied_ai/chatbot_cli.py


class ChatBot:
    def __init__(self, client: Groq, settings: Settings, system_prompt: str) -> None: ...
    # history: list[ChatCompletionMessageParam]  # mensajes confirmados (empieza en [system])
    def chat(self, user_message: str) -> str: ...
```

- `client` y `settings` se **inyectan** (patrón coherente con `call_ai` en 02-06).
- `system_prompt` es un **parámetro del constructor**, no un campo de `Settings` ni un literal hardcodeado: así es reutilizable y testeable. **No se copia el texto original del curso/Gist**; pase su propia instrucción en español al instanciar.

### Comportamiento transaccional de `chat`

1. Construir `user_param` (TypedDict `user`) a partir de `user_message`.
2. Construir `pending = [*self.history, user_param]` **sin mutar** `self.history`.
3. Llamar `client.chat.completions.create(model=..., messages=pending, ...)`.
4. Si la llamada **lanza** (p. ej. `APIConnectionError`), la excepción se **propaga** al límite de CLI (igual que 02-06) y `self.history` **queda igual**.
5. Si la llamada **tiene éxito**, extraer `content` (vacío `""` si es `None`) y recién entonces hacer `self.history.append(user_param)` y `self.history.append(assistant_param)`.

Esto garantiza que un fallo de red no deje medio mensaje colgado en el historial.

### Decisión de contenido vacío (comportamiento aceptado)

Decisión del análisis aprobado: si `response.choices[0].message.content` es `None`, `chat` **devuelve `""` y confirma un mensaje assistant con `""`** en el historial.

- **Tradeoff:** confirmar `""` mantiene el historial alineado con la respuesta del modelo (el asistente "dijo" nada), útil para depurar y para no romper turnos siguientes. El riesgo es almacenar un turno vacío que no aporta contexto.
- **Comportamiento de aceptación:** el test T5 verifica exactamente este contrato (devuelve `""`, confirma assistant con `""`). Si en su implementación prefiere fallar sin mutar, cámbielo y actualice T5 en consecuencia; esta guía fija la opción "devolver/confirmar vacío".

### Parámetros de la llamada

- `model=settings.llm_model`
- `max_tokens=settings.llm_max_tokens` (actualmente soportado)
- `temperature=validate_temperature(settings.llm_temperature)` (configuración introducida en 02-07)
- `top_p=0.9` (coherente con 02-06)

> **Nota de migración (`max_tokens`):** en los tipos del SDK, `max_tokens` está **deprecado** a favor de `max_completion_tokens`. En `openai/gpt-oss-20b` los **tokens de razonamiento cuentan dentro del presupuesto de `completion_tokens`**. Esta guía mantiene `max_tokens` para compatibilidad con el proyecto actual; evalúe la migración a `max_completion_tokens` sin prisa y sin cambiar el comportamiento hoy.

### `total_tokens` / `total_cost`

- El seguimiento acumulado de tokens/costo se difiere a 02-09; el bucle y `format_stats`, a 02-10.
- El costo usa `Decimal` (en `cost.py`), **nunca `float`**, para evitar errores de redondeo de moneda. Las tarifas son `Decimal | None` opcionales en `Settings`; hoy no se exige su configuración.
- El `system_prompt` pedagógico es `You are a helpful Python and AI assistant.`; en tests use un fixture aislado (no mezcle el prompt de producción con el de test).

### `chatbot_cli.py` (implementación)

```python
from groq import Groq
from groq.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from python_applied_ai.config import Settings
from python_applied_ai.sampling import validate_temperature


class ChatBot:
    """Maintain one CLI chatbot session in memory."""

    def __init__(self, client: Groq, settings: Settings, system_prompt: str) -> None:
        self.client = client
        self.settings = settings
        self.history: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        ]

    def chat(self, user_message: str) -> str:
        """Send one message and commit a successful conversation round."""
        user_entry = ChatCompletionUserMessageParam(role="user", content=user_message)
        pending_history: list[ChatCompletionMessageParam] = [*self.history, user_entry]
        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=pending_history,
            max_tokens=self.settings.llm_max_tokens,
            temperature=validate_temperature(self.settings.llm_temperature),
            top_p=0.9,
        )
        content = response.choices[0].message.content or ""
        assistant_entry = ChatCompletionAssistantMessageParam(role="assistant", content=content)
        self.history.append(user_entry)
        self.history.append(assistant_entry)
        return content
```

> El `system_prompt` se pasa al instanciar (p. ej. `ChatBot(client, settings, "<tu instrucción de sistema en español>")`). **No se incluye aquí el texto original del curso ni del Gist**; use su propia redacción.

## Plan de TDD (behavior-first, offline)

Cero llamadas reales a la API. Patrón **AAA** (Arrange – Act – Assert):

- **Arrange:** construir `Settings` de confianza (`Settings.model_construct`, solo en tests) y un cliente falso (`MagicMock`) cuyo `chat.completions.create` devuelve o lanza lo controlado.
- **Act:** invocar `bot.chat(...)`.
- **Assert:** verificar mensajes enviados, historial confirmado y/o excepción propagada.

### Cómo construir un mock válido de `ChatCompletion`

El tipo real `ChatCompletion` es complejo. Para mantener mypy strict plausible sin mecanografía completa, se usa `MagicMock` con `cast(ChatCompletion, ...)`:

```python
# tests/test_chatbot_cli.py — helper de respuesta offline.
from typing import cast
from unittest.mock import MagicMock
from groq.types.chat import ChatCompletion


def _fake_completion(content: str | None) -> ChatCompletion:
    """Build a ChatCompletion-shaped fake without network.

    Only the fields our code reads: choices[0].message.content.
    cast keeps mypy strict happy; the MagicMock supplies the rest.
    """
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    return cast(ChatCompletion, resp)
```

El helper de error de conexión reusa el de 02-06 (request en memoria, sin red):

```python
# tests/test_chatbot_cli.py — patrón de error verificado en 02-06.
import httpx
from groq import APIConnectionError


def _fake_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.groq.com/v1/chat/completions")


def _connection_error() -> APIConnectionError:
    return APIConnectionError(message="Connection failed", request=_fake_request())
```

El helper de `Settings` (solo tests) también reusa 02-06:

```python
# tests/test_chatbot_cli.py — Settings de confianza, sin .env ni red.
from python_applied_ai.config import Settings


def _test_settings() -> Settings:
    return Settings.model_construct(
        llm_model="openai/gpt-oss-20b",
        llm_max_tokens=256,
    )
```

`Settings.model_construct` está confinado a `tests/`: construye un fixture de confianza sin validar ni cargar fuentes de entorno. No debe usarse en `src/`.

### `tests/test_chatbot_cli.py` (implementación offline)

```python
# tests/test_chatbot_cli.py — offline, AAA; cero red, cuota y .env.
from typing import cast
from unittest.mock import MagicMock

import httpx
import pytest
from groq import APIConnectionError, Groq
from groq.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from python_applied_ai.chatbot_cli import ChatBot
from python_applied_ai.config import Settings

SYSTEM_PROMPT = "<tu instrucción de sistema en español>"  # placeholder, no copiado


# T1: el historial inicial contiene solo el mensaje system.
def test_initial_history_has_system_message() -> None:
    settings = _test_settings()
    fake_client = MagicMock()

    bot = ChatBot(cast(Groq, fake_client), settings, SYSTEM_PROMPT)

    assert len(bot.history) == 1
    sys_msg = cast(ChatCompletionSystemMessageParam, bot.history[0])
    assert sys_msg["role"] == "system"
    assert sys_msg["content"] == SYSTEM_PROMPT
    # No se llamó a la API al construir.
    fake_client.chat.completions.create.assert_not_called()


# T2: primera ronda envía [system, user], devuelve contenido y confirma [system, user, assistant].
def test_first_round_roundtrips_history() -> None:
    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_completion("Hola")

    bot = ChatBot(cast(Groq, fake_client), settings, SYSTEM_PROMPT)

    reply = bot.chat("Hola")

    assert reply == "Hola"
    _, kwargs = fake_client.chat.completions.create.call_args
    sent = kwargs["messages"]
    assert len(sent) == 2
    assert sent[0]["role"] == "system"
    assert sent[1]["role"] == "user"
    # Historial confirmado: system + user + assistant.
    assert len(bot.history) == 3
    assistant = cast(ChatCompletionAssistantMessageParam, bot.history[2])
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "Hola"


# T3: la segunda ronda envía el contexto previo completo.
def test_second_round_sends_full_context() -> None:
    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_completion("First reply"),
        _fake_completion("Second reply"),
    ]

    bot = ChatBot(cast(Groq, fake_client), settings, SYSTEM_PROMPT)
    bot.chat("First question")
    bot.chat("Second question")

    second_call = fake_client.chat.completions.create.call_args_list[1]
    assert second_call.kwargs["messages"] == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First reply"},
        {"role": "user", "content": "Second question"},
    ]


# T4: APIConnectionError se propaga y el historial queda sin cambios.
def test_connection_error_propagates_and_history_unchanged() -> None:
    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = _connection_error()

    bot = ChatBot(cast(Groq, fake_client), settings, SYSTEM_PROMPT)

    with pytest.raises(APIConnectionError):
        bot.chat("Hola")

    # Solo el mensaje system: el fallo no mutó el historial.
    assert len(bot.history) == 1


# T5: content None devuelve "" y confirma un assistant con "".
def test_empty_content_returns_empty_string_and_commits() -> None:
    settings = _test_settings()
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_completion(None)

    bot = ChatBot(cast(Groq, fake_client), settings, SYSTEM_PROMPT)

    reply = bot.chat("Hola")

    assert reply == ""
    assert len(bot.history) == 3
    assistant = cast(ChatCompletionAssistantMessageParam, bot.history[2])
    assert assistant["content"] == ""
```

> Esta etapa añade **5 casos** T1–T5, todos offline. Sumados al checkpoint de 02-07, quedan **51 tests acumulados**.

## Procedimiento manual de aprendizaje

1. Confirme 02-05, 02-06 y 02-07 Completed.
2. Implemente únicamente `ChatBot`, historial y `chat() -> str`; no copie todavía `ChatTurn`, estadísticas ni bucle CLI del árbol final.
3. Revise `tests/test_chatbot_cli.py`: T1–T5 son pruebas offline de comportamiento y caracterización.
4. Ejecute `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src tests`, `uv run pytest tests/test_chatbot_cli.py -q` y `uv run pytest -q`.
5. Una llamada en vivo es opcional y consume cuota; no se ejecutó para esta Parte 1 y nunca se deben provocar errores a propósito.

## Observaciones esperadas (sin prometer salidas exactas)

- Tras T2, `bot.history` tiene 3 entradas y la API recibió exactamente `[system, user]`.
- Tras T3, la API recibió 4 mensajes (contexto acumulado).
- En T4, la excepción llega al llamador y `len(bot.history) == 1`.
- En T5, `chat` devuelve `""` y el historial incluye un assistant con `""`.

## Preguntas de análisis

- ¿Por qué reenviamos `system` en cada turno y no solo al inicio?
- ¿Qué pasa con los tokens/latencia/costo a medida que crece el historial?
- ¿Por qué `chat` no captura `APIConnectionError` (lo deja propagar)?
- ¿Por qué confirmar el historial solo tras una respuesta exitosa?
- ¿Por qué el costo usa `Decimal` y no `float`?

## Errores comunes

- Mutar `self.history` antes de confirmar la respuesta (historial corrupto tras fallo).
- Capturar `Exception` o `GroqError` dentro de `chat` (acopla dominio a presentación).
- Hardcodear el modelo/system prompt/tarifas en la clase (rompe provider-neutrality).
- Usar `float` para tarifas o costo (error de redondeo de moneda).
- Pretender que RAG reemplaza la memoria de chat.
- Crear el bucle de CLI o el banner en esta lección (corresponde a 02-10).

## Checklist de aceptación

- [x] `ChatBot.__init__(client: Groq, settings: Settings, system_prompt: str)` inyecta cliente y settings.
- [x] `history` empieza en `[system]` (rol `system`, contenido = `system_prompt`).
- [x] `chat` construye `pending` sin mutar `history` y confirma user+assistant solo tras éxito.
- [x] `chat` usa modelo, límite y temperatura desde `Settings`; `top_p=0.9` permanece fijo en esta sección.
- [x] Los errores de Groq se propagan al límite (no se capturan en dominio).
- [x] `content is None` → devuelve `""` y confirma assistant con `""` (contrato T5).
- [x] Sin contadores muertos ni responsabilidades adelantadas de 02-09/02-10.
- [x] Pruebas T1–T5 offline (MagicMock/`cast`, `Settings.model_construct`); cero red/cuota.
- [x] 5 pruebas nuevas del chatbot y **51 tests acumulados** en verde.
- [x] No se copió código del Gist ni del curso de pago.

## Comandos de verificación

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest tests/test_chatbot_cli.py -q   # 5 tests en esta etapa
uv run pytest -q                            # 51 tests acumulados
```

## Rollback / límite de parada

- Si `mypy --strict` falla por tipos de historial, use `cast(...)` a la TypedDict concreta (ver tests).
- Si una llamada en vivo falla, **deténgase**; no agregue bucles ni reintentos manuales (el SDK reintenta por sí solo).
- No edite `.env` ni desactive la red para "provocar" fallos: use el cliente falso en pruebas.

## Siguiente paso

El chatbot ya mantiene historial de forma transaccional y consume `settings.llm_temperature`. Continúe con [02-09-cli-chatbot-session-usage-and-cost.md](./02-09-cli-chatbot-session-usage-and-cost.md) para añadir `ChatTurn` y estadísticas sin contaminar el dominio con presentación.

## Referencias externas oficiales

- groq-python (chat completions/types): https://github.com/groq/groq-python
- Documentación de Groq (chat completions): https://console.groq.com/docs/chat
- Modelos y límites: https://console.groq.com/docs/models
- Modelo GPT-OSS 20B: https://console.groq.com/docs/model/openai/gpt-oss-20b
- Implementación pública final del curso (solo comparación **después** de implementar, **no copiar**): repositorio `https://github.com/ricardocuellar/devtalles-python-inteligencia-artificial-aplicada.git`, rama `section-2-fundamentos` (enlace volátil; términos educativos; esta guía no reproduce su código ni commits).
- Fuente externa de arranque (OpenAI), **no copiar**: Gist público `https://gist.github.com/ricardocuellar/e018baefacfdcccef325b596bedec0ee` (enlace volátil; esta guía es autónoma y no lo reproduce).
