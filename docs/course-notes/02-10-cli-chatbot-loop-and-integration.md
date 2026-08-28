# Chatbot en CLI: bucle e integración final (Parte 3)

> **Aviso de privacidad y procedencia:** esta guía es una adaptación original de conceptos. No reproduce transcripciones ni código de terceros y excluye medios, metadatos, credenciales, tarifas privadas, identificadores de respuesta y rutas personales.

## Estado

**Planned** — tercera y última parte del proyecto CLI. Requiere [02-08-cli-chatbot-conversation-history.md](./02-08-cli-chatbot-conversation-history.md) y el contrato de resultados/estadísticas planificado en [02-09-cli-chatbot-session-usage-and-cost.md](./02-09-cli-chatbot-session-usage-and-cost.md).

## Resultado esperado

Una función de ejecución de terminal testable recibe entradas normalizadas, llama solo a las APIs públicas de `ChatBot`, muestra respuestas y estadísticas seguras, y finaliza de forma predecible ante comandos, EOF, Ctrl+C o errores tipados de Groq.

## Ruta rápida

1. Construir el chatbot y sus dependencias en una fábrica de borde, no dentro de la lógica testeable del bucle.
2. Usar una función `run_cli(...)` con `input_fn` y `output_fn` inyectados para pruebas sin terminal ni red.
3. Normalizar entradas, ignorar blancos y tratar comandos antes de llamar al modelo.
4. Renderizar `ChatTurn.text`, nunca una cadena como si fuera una `ChatCompletion`.
5. Capturar excepciones específicas y terminar mostrando el resumen exactamente una vez.

## Límites

| Incluido | Fuera de alcance |
| --- | --- |
| Bucle interactivo y comandos | Interfaz web, streaming o persistencia |
| Renderizado de respuestas y estadísticas | Reintentos manuales o recuperación automática |
| Manejo seguro de EOF/Ctrl+C/errores tipados | Modificar historial desde `main` |

## Diseño del límite CLI

El dominio conserva historial y estadísticas. La terminal solo coordina entradas/salidas. Para probarlo, el bucle no debe crear un cliente real ni leer configuración directamente.

```python
# PLANNED: src/python_applied_ai/chatbot_cli.py
from collections.abc import Callable

from groq import (
    APIConnectionError,
    AuthenticationError,
    GroqError,
    NotFoundError,
    RateLimitError,
)


EXIT_COMMANDS = frozenset({"quit", "exit", "salir", "bye"})


def run_cli(
    bot: ChatBot,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Run a testable terminal loop around public ChatBot APIs."""
    try:
        while True:
            try:
                raw_input = input_fn("You: ")
            except EOFError:
                output_fn("Input closed. Ending session.")
                break

            command = raw_input.strip()
            normalized = command.lower()
            if not command:
                continue
            if normalized in EXIT_COMMANDS:
                break
            if normalized == "/stats":
                output_fn(format_stats(bot.stats()))
                continue
            if normalized == "/reset":
                bot.reset_session()
                output_fn("Conversation reset.")
                continue

            try:
                turn = bot.chat(command)
            except AuthenticationError:
                output_fn("Authentication failed. Check the configured API key.")
            except RateLimitError:
                output_fn("Rate limit reached. Try again later; do not loop.")
            except NotFoundError:
                output_fn("Configured model was not found.")
            except APIConnectionError:
                output_fn("Connection error. Check the network and retry later.")
            except GroqError:
                output_fn("Unexpected Groq error. Try again later or check the status page.")
            else:
                output_fn(turn.text)
    except KeyboardInterrupt:
        output_fn("\nSession interrupted.")
    finally:
        output_fn(format_stats(bot.stats()))
```

Los nombres son planificados: `stats()`, `reset_session()` y `format_stats()` deben provenir del contrato de 02-09. El orden específico→genérico evita que `GroqError` capture antes a sus subclases. Ningún mensaje imprime el detalle crudo del proveedor.

## Comandos de la conversación

| Entrada normalizada | Acción |
| --- | --- |
| Cadena vacía | No hace nada; vuelve a pedir entrada. |
| `quit`, `exit`, `salir`, `bye` | Sale sin llamar al modelo. |
| `/stats` | Muestra el resumen actual; no cambia historial. |
| `/reset` | Usa `bot.reset_session()`; conserva el mensaje system. |
| Otro texto | Ejecuta un turno y muestra `turn.text`. |

No hay acceso directo a `bot.history` desde el bucle. Esta regla evita que la capa de presentación rompa la atomicidad definida en 02-08.

## Prevención de un error de contrato común

Una completación completa contiene texto y uso; el texto solo es un `str`. Pasar o reutilizar el texto como si tuviera `.usage` rompe el flujo de estadísticas. El contrato `ChatTurn` de 02-09 elimina esa ambigüedad: el bucle imprime `turn.text`; el dominio usa `turn.usage` para sus acumulados antes de devolverlo.

## Plan de pruebas offline

`run_cli` debe recibir un chatbot falso o un `MagicMock` con una interfaz explícita, una secuencia de entradas y un `output_fn` que acumule líneas. No se crea `Groq()`, no se lee `.env` y no se realizan llamadas reales.

| Caso | Prueba |
| --- | --- |
| Blanco | No llama `bot.chat`. |
| Salida | Un alias termina sin llamada al modelo. |
| `/stats` | Llama `bot.stats()` y no muta conversación. |
| `/reset` | Llama `bot.reset_session()` y confirma el mensaje de salida. |
| Turno normal | Imprime `ChatTurn.text`, no el objeto completo. |
| Error tipado | Muestra mensaje fijo seguro sin detalle crudo. |
| EOF/Ctrl+C | Termina limpiamente. |
| Finalización | Muestra estadísticas exactamente una vez. |

No se usa `except Exception`, `sleep`, reintento manual ni salida forzada del proceso. `KeyboardInterrupt` y `EOFError` son condiciones de interfaz, no errores de proveedor.

## Checklist de aceptación

- [ ] `run_cli` es testeable mediante funciones de entrada/salida inyectadas.
- [ ] Los comandos se normalizan y los blancos no llaman al modelo.
- [ ] `main` usa solo APIs públicas del chatbot.
- [ ] `/reset` conserva el system prompt mediante una API del dominio.
- [ ] Los errores Groq se capturan en orden específico→genérico con mensajes fijos.
- [ ] El resumen final aparece una vez para salida normal, EOF o Ctrl+C.
- [ ] Todas las pruebas son offline; no hay `except Exception` ni reintentos manuales.
- [ ] Ruff, mypy y pytest pasan antes de declarar el proyecto terminado.

## Comandos previstos

```bash
uv run ruff format --check .
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q
```

## Siguiente paso

Implementar primero 02-09 mediante TDD. Después, esta guía integrará el chatbot terminado y cerrará la sección 2.

## Referencias oficiales

- Groq Python SDK: https://github.com/groq/groq-python
- Manejo de errores del SDK: https://github.com/groq/groq-python/blob/main/README.md
