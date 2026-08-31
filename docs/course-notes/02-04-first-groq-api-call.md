# Primera llamada a la API de Groq

> **Aviso de derechos y privacidad:** Este documento es una nota de estudio independiente que resume objetivos de aprendizaje y decisiones originales de implementación. No reproduce transcripciones de cursos de pago ni material con derechos de autor. No incluye claves de API reales, datos personales ni activos de video.

## Estado

**Completed — etapa 3 de 9.** Parte de la API key segura de 02-03 y añade `Settings`, `hello_ai.py` y la primera llamada. El checkpoint mantiene **1 test automatizado** de infraestructura y añade un smoke test live manual; uso, costo, errores tipados y temperatura llegan en etapas posteriores.

## Objetivo de aprendizaje

Realizar la primera llamada a Groq cargando configuración tipada, enviando un único mensaje y mostrando la respuesta. El manejo detallado de errores se incorpora deliberadamente en 02-06.

## Ruta rápida

1. (Hecho) Añadir `LLM_MAX_TOKENS=256` a `.env.example` y al `.env` privado.
2. (Hecho) Crear `src/python_applied_ai/config.py` con `pydantic-settings`.
3. (Hecho) Crear `src/python_applied_ai/hello_ai.py` con el cliente de Groq.
4. (Hecho) Ejecutar `uv run python -m python_applied_ai.hello_ai` desde la raíz del repositorio.
5. (Hecho) Verificar con `ruff format .`, `ruff check .`, `mypy src` y `pytest`.

## Resumen del concepto del instructor

La lección original "Tu primera llamada a la API" del curso muestra el flujo básico: cargar las variables de entorno, crear el cliente del proveedor, realizar una sola llamada con un mensaje y mostrar la respuesta. Esta nota conserva ese flujo y lo adapta a Groq con configuración tipada. No se reproduce el texto del curso.

## Nuestra adaptación Groq y tabla de mapeo

| Concepto (OpenAI original) | Adaptación Groq |
| --- | --- |
| Cliente `OpenAI(api_key=...)` | Cliente `Groq(api_key=...)` |
| `openai` SDK | `groq` SDK (endpoints de chat compatibles) |
| Variables `OPENAI_API_KEY` / modelo `gpt-*` | `GROQ_API_KEY` / modelo `openai/gpt-oss-20b` |
| `max_tokens` en la llamada | `max_tokens` desde `settings.llm_max_tokens` |

## Añadir `LLM_MAX_TOKENS` al entorno

La línea `LLM_MAX_TOKENS=256` ya está presente en `.env.example` (rastreado) y en el `.env` privado:

```text
LLM_MAX_TOKENS=256
```

El valor por defecto en código también es `256`; la variable permite ajustarlo sin tocar el código.

## Implementación: `src/python_applied_ai/config.py`

```python
"""Typed application settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env and environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-20b"
    groq_api_key: SecretStr | None = None
    llm_max_tokens: int = 256


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
```

Notas clave:

- `extra="ignore"` es obligatorio porque el `.env` compartido también define `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL` y `OLLAMA_MODEL`, que no son campos declarados.
- `groq_api_key` es `SecretStr | None`; el valor solo se materializa en el constructor del cliente vía `get_secret_value()`.
- `get_settings()` es la función de fábrica usada por `hello_ai.py` (no se importa la clase `Settings` directamente en el módulo de ejecución).

## Implementación: `src/python_applied_ai/hello_ai.py`

```python
from groq import Groq
from groq.types.chat import ChatCompletion

from python_applied_ai.config import Settings, get_settings


def call_ai(client: Groq, question: str, settings: Settings) -> ChatCompletion:
    return client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": question}],
        max_tokens=settings.llm_max_tokens,
        temperature=0.7,
        top_p=0.9,
    )


def main() -> None:
    settings = get_settings()
    if not settings.groq_api_key:
        print("Missing GROQ API KEY. Add it to .env and retry.")
        return

    client = Groq(api_key=settings.groq_api_key.get_secret_value())
    response = call_ai(client, "Say hello in three languages.", settings)
    print(response.choices[0].message.content or "")
```

Este es el **estado didáctico de 02-04**, no el archivo final. 02-05 añade uso/costo, 02-06 introduce errores tipados y 02-07 reemplaza la temperatura literal por configuración validada.

## Ejecución

```bash
uv run python -m python_applied_ai.hello_ai
```

Ejecute el comando desde la **raíz del repositorio** para que `.env` se resuelva por el directorio de trabajo actual. No use `load_dotenv`; `pydantic-settings` ya carga el archivo.

## Tarea (homework)

Salude en español, inglés y francés modificando el mensaje de usuario. Mantenga `LLM_MAX_TOKENS=256`; bajar a `128` es una opción de ajuste de costo más estricto, **no** un aumento.

**Estado:** Completa. La ejecución en vivo de `uv run python -m python_applied_ai.hello_ai` realizó la llamada real a Groq y devolvió las tres salutaciones en el orden esperado (español, inglés, francés). No se incluye transcripción literal del curso; la evidencia es la salida real de la API (tres saludos, uno por lengua).

## Verificación

Estos comandos se ejecutaron tras implementar el código. No se afirma más de lo verificado:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
```

- `ruff` no reportó errores de formato ni de lint.
- `mypy` (modo strict) no reportó errores de tipos (9 archivos fuente).
- `pytest` conserva verde el test de infraestructura de esta etapa.
- Llamada en vivo: el módulo `hello_ai.py` realizó la llamada real a Groq y devolvió las tres salutaciones.

## Decisión, trade-offs y errores comunes

- **Contrato `Settings` → `Groq` → `call_ai`/`response`**: esta etapa configura key, modelo y límite de tokens. `call_ai` encapsula una única llamada; las responsabilidades de reporte y errores se añaden en 02-05/02-06.
- **Live vs offline**: `hello_ai.py` ejecuta llamadas reales a Groq cuando se invoca con `uv run python -m python_applied_ai.hello_ai`. Las pruebas de `test_hello_ai.py` son 100 % offline (MagicMock, sin red ni cuota). La verificación offline confirma el comportamiento del manejo de errores; la verificación live confirma el flujo feliz con la API real. Ambos son complementarios, no sustitutos.
- **`extra="ignore"` obligatorio**: sin él, `SettingsConfigDict(env_file=".env")` lanza `ValidationError` (`extra_forbidden`) por las variables no declaradas del `.env` compartido.
- **`SecretStr`**: endurece el manejo del secreto; nunca se imprime ni se registra su longitud.
- **`pydantic-settings` no exporta a `os.environ`**: pase `api_key` explícitamente a `Groq(api_key=...)`.
- **Ejecución por módulo desde la raíz**: `python -m python_applied_ai.hello_ai` asegura que `.env` se resuelva por el cwd.
- **Errores de Groq**: se importan del paquete de nivel superior `groq`, no de `groq.types`.
- **`max_tokens`**: válido para `openai/gpt-oss-20b`; los modelos de razonamiento pueden documentar además `max_completion_tokens`. Los tokens de razonamiento cuentan hacia el límite; aumente el valor si la respuesta se trunca.
- **`get_settings()`**: `hello_ai.py` usa la función de fábrica en lugar de instanciar `Settings()` directamente.

## Resultado de etapa y siguiente paso

Con la cuenta/key lista (`02-03-groq-account-api-key.md`) y el andamiaje completo (`02-02-project-scaffold.md`), `config.py` y `hello_ai.py` existen y ambas llamadas en vivo pasaron (saludo único y tarea de tres lenguas). El siguiente paso es [02-05-token-usage-and-cost-estimation.md](./02-05-token-usage-and-cost-estimation.md) (uso de tokens y estimación de costo), ahora desbloqueado por esta lección.

## Mensaje de commit sugerido

```text
feat: add typed Groq config and first API call module
```

No se realiza commit ni push en este paso; queda a decisión del usuario.

## Referencias externas oficiales

- groq-python: https://github.com/groq/groq-python
- Documentación de Groq: https://console.groq.com/docs/quickstart
- Modelo: https://console.groq.com/docs/model/openai/gpt-oss-20b
