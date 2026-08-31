# Chatbot en CLI: bucle e integración final (Parte 3)

> **Aviso de privacidad y procedencia:** esta guía es una adaptación original de conceptos. No reproduce transcripciones ni código de terceros y excluye medios, metadatos, credenciales, tarifas privadas, identificadores de respuesta y rutas personales.

## Estado

**Completado** — tercera y última parte del proyecto CLI. El núcleo del dominio (`ChatBot`, `ChatTurn`, `SessionStats`, `format_stats`), el bucle `run_cli` y el cableado del punto de entrada ejecutable están implementados y verificados offline (46 tests verdes; Ruff format/lint, mypy y diff checks limpios). El smoke test en vivo confirmó el flujo interactivo completo: `uv run python-applied-ai` abrió `You:`, la primera consulta real respondió, `/stats` y `/reset` funcionaron, y `exit` imprimió las estadísticas finales exactamente una vez y volvió a consola. Requiere [02-08-cli-chatbot-conversation-history.md](./02-08-cli-chatbot-conversation-history.md) y el contrato de resultados/estadísticas **ya implementado** en [02-09-cli-chatbot-session-usage-and-cost.md](./02-09-cli-chatbot-session-usage-and-cost.md).

## Resultado esperado

Una función de ejecución de terminal testable recibe entradas normalizadas, llama solo a las APIs públicas de `ChatBot`, muestra respuestas y estadísticas seguras, y finaliza de forma predecible ante comandos, EOF, Ctrl+C o errores tipados de Groq. El punto de entrada ejecutable (`python-applied-ai`) debe orquestar la construcción del borde sin exponer credenciales ni detalles crudos del proveedor.

## Ruta rápida

1. Construir el chatbot y sus dependencias en una fábrica de borde, no dentro de la lógica testeable del bucle.
2. Usar una función `run_cli(...)` con `input_fn` y `output_fn` inyectados para pruebas sin terminal ni red.
3. Normalizar entradas, ignorar blancos y tratar comandos antes de llamar al modelo.
4. Renderizar `ChatTurn.text`, nunca una cadena como si fuera una `ChatCompletion`.
5. Capturar excepciones específicas y terminar mostrando el resumen exactamente una vez.
6. **Completado:** cableado de `src/python_applied_ai/__init__.py::main` al constructor de borde y a `run_cli` (sección `Integración completada`).

## Límites

| Incluido | Fuera de alcance |
| --- | --- |
| Bucle interactivo y comandos | Interfaz web, streaming o persistencia |
| Renderizado de respuestas y estadísticas | Reintentos manuales o recuperación automática |
| Manejo seguro de EOF/Ctrl+C/errores tipados | Modificar historial desde `main` |
| Punto de entrada ejecutable cableado a `run_cli` | Llamadas en vivo hasta smoke test controlado |

## Diseño del límite CLI

El dominio conserva historial y estadísticas. La terminal solo coordina entradas/salidas. Para probarlo, el bucle no debe crear un cliente real ni leer configuración directamente.

`run_cli` y `format_stats` están implementados en `src/python_applied_ai/chatbot_cli.py` (02-10). `stats()` y `reset_session()` ya existen en 02-09. El bucle invoca `bot.stats()` y `bot.reset_session()` según el contrato ya existente. El orden específico → genérico evita que `GroqError` capture antes a sus subclases. Ningún mensaje imprime el detalle crudo del proveedor.

```python
# Implementado en src/python_applied_ai/chatbot_cli.py (02-10):
# run_cli y format_stats; stats() y reset_session() ya existen (02-09).
# Pruebas del núcleo: 46 verdes (02-10).
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

## Integración completada

El punto de entrada ejecutable `python-applied-ai` ahora orquesta el borde completo sin exponer credenciales.

1. **Punto de entrada registrado.** `pyproject.toml` expone `python-applied-ai = "python_applied_ai:main"`.
2. **`__init__.py::main` cableado.** La función `main` carga `Settings` (mediante `get_settings()`), valida que `GROQ_API_KEY` esté presente (avisa sin tracear y sale si falta), construye un cliente `Groq` con la clave, instancia `ChatBot(client, settings, system_prompt)` e invoca `run_cli(bot)`.
3. **Validación segura.** La clave solo se verifica por presencia/ausencia bajo el nombre `GROQ_API_KEY`; nunca se imprime ni registra. El modelo configurado es `openai/gpt-oss-20b`.
4. **Función `hello_ai.py::main`.** `src/python_applied_ai/hello_ai.py` contiene una función `main()` de llamada única a la API (`call_ai` + `report_usage`). **No sustituye** el bucle interactivo de `chatbot_cli.run_cli`; es otro camino de ejecución, no el CLI conversacional.
5. **Verificación en vivo.** `uv run python-applied-ai` abrió `You:`, la primera consulta real respondió, `/stats` y `/reset` funcionaron, y `exit` imprimió las estadísticas finales exactamente una vez y volvió a consola.

Nunca se imprimen ni registran valores crudos de `GROQ_API_KEY` ni de la clave del proveedor; la validación solo comprueba presencia/ausencia usando el nombre de variable `GROQ_API_KEY`.

## Comandos de la conversación

| Entrada normalizada | Acción |
| --- | --- |
| Cadena vacía | No hace nada; vuelve a pedir entrada. |
| `quit`, `exit`, `salir`, `bye` | Sale sin llamar al modelo. |
| `/stats` | Muestra el resumen actual; no cambia historial. |
| `/reset` | Usa `bot.reset_session()`; conserva el system prompt. |
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

Las pruebas de `tests/test_chatbot_cli.py` cubren el bucle `run_cli` (salida, `/stats`, `/reset`, turno normal, errores tipados, EOF, `KeyboardInterrupt`) de forma 100 % offline. La cobertura del slice de integración del punto de entrada se describe a continuación. Pruebas del núcleo: 46 verdes.

## Plan TDD / aceptación para el slice de integración *(histórico — verificación completada)*

Objetivo original: verificar que `python_applied_ai.main` orquesta el borde completo **antes** de cualquier prueba en vivo.

1. **Test offline del camino ejecutable** — **Completado**:
   - Fixture: `Settings.model_construct` con `groq_api_key` presente (`SecretStr`) y tarifas de prueba.
   - Patch de `get_settings` → retorna el fixture con `SecretStr` presente.
   - Patch del constructor `Groq` → verificar que recibe la clave sin imprimirla ni registrarla.
   - Patch del constructor `ChatBot` → verificar que recibe el cliente, `settings` y `system_prompt` esperados.
   - Patch de `run_cli` → verificar que recibe el `ChatBot` construido.
   - Variante sin clave: patch de `get_settings` sin `groq_api_key` → no construir `Groq` ni `ChatBot`, no llamar a `run_cli`, y emitir un mensaje seguro de clave faltante.
2. **Caja blanca del constructor de borde** — **Completado**:
   - El constructor de borde no imprime ni devuelve la clave; solo valida presencia.
   - `Groq` se construye solo cuando `get_settings` retorna una clave presente.
   - `main` delega la interacción y los errores tipados a `run_cli`; no añade `except Exception` ni duplica handlers.
3. **Smoke test en vivo** — **Completado** (solo tras pasar el punto anterior):
   - `.env` con `GROQ_API_KEY` válida.
   - `uv run python-applied-ai` y recorrido interactivo básico (sección `Prueba manual segura`).

No se fusionó el cableado del punto de entrada sin el test offline primero; el smoke test en vivo fue validación complementaria, no sustituto.

## Prueba manual segura

Objetivo: confirmar que el ejecutable funciona sin exponer credenciales ni valores no deterministas.

1. **Verificar `.env` sin mostrar la clave.**
   - Confirmar que `.env` existe y contiene `GROQ_API_KEY` con un valor válido y el modelo esperado (`openai/gpt-oss-20b`).
   - No imprimir, loguear ni copiar el valor de la clave; la validación es de presencia/ausencia.
2. **Ejecutar el punto de entrada.**
   - Comando: `uv run python-applied-ai`.
   - Resultado esperado: aparece el prompt `You: ` sin errores de importación ni de configuración. Si `GROQ_API_KEY` falta, debe avisar de forma segura y salir.
3. **Hacer una pregunta.**
   - Entrada: una frase corta (p. ej. `Hola`).
   - Resultado esperado: el modelo devuelve una respuesta textual y se muestra `turn.text`. No se imprime el objeto completo ni detalles internos del proveedor.
4. **Comando `/stats`.**
   - Resultado esperado: resumen de la sesión con `Turns`, `Prompt tokens`, `Completion tokens`, `Total tokens` y costo teórico; no muta el historial.
5. **Comando `/reset`.**
   - Resultado esperado: mensaje `Conversation reset.` y el historial vuelve al estado inicial (solo system).
6. **Otra pregunta y `exit`.**
   - Entrada: una segunda pregunta y después `exit`.
   - Resultado esperado: respuesta normal, y al salir el resumen final se muestra exactamente una vez.

Resultados no deterministas: el cuerpo de la respuesta del modelo varía; las estadísticas numéricas dependen del uso real. Verificar el **formato** y la **presencia** de las secciones, no el texto exacto.

### Resultado verificado (smoke test en vivo)

- `uv run python-applied-ai` abrió el prompt `You:` sin errores de importación ni configuración.
- Primera consulta real: el modelo respondió; `/stats` mostró `Turns 1`, 93/72/165 tokens, costo 0.000028575.
- `/reset` respondió `Conversation reset.`.
- Segunda consulta real: el modelo respondió; `/stats` mostró `Turns 1`, 91/256/347 tokens, costo 0.000083625.
- `exit` imprimió las estadísticas finales exactamente una vez y regresó a la consola.
- **Límite esperado `LLM_MAX_TOKENS=256`:** el completion de 256 tokens alcanzó el tope configurado; es un límite esperado, no un error. El comportamiento se ajusta a la configuración del modelo.

No se copiaron respuestas del modelo ni credenciales en esta guía; la clave (`GROQ_API_KEY`) permanece fuera del documento.

## Checklist de aceptación

- [x] `run_cli` es testeable mediante funciones de entrada/salida inyectadas.
- [x] Los comandos se normalizan y los blancos no llaman al modelo.
- [x] `main` usa solo APIs públicas del chatbot; cableado a `run_cli` completado.
- [x] `/reset` conserva el system prompt mediante una API del dominio.
- [x] Los errores Groq se capturan en orden específico → genérico con mensajes fijos.
- [x] El resumen final aparece una vez para salida normal, EOF o Ctrl+C.
- [x] Todas las pruebas del bucle son offline; no hay `except Exception` ni reintentos manuales.
- [x] `format_stats` implementado y verificado en `chatbot_cli.py`.
- [x] Ruff, mypy y pytest pasan en el núcleo del dominio (46 tests).
- [x] `hello_ai.py::main` documentado como función de llamada única, no sustituto del bucle.
- [x] Punto de entrada `python-applied-ai` ejecuta el bucle CLI completo.
- [x] Test offline de `main` con inyección/mocks antes de smoke test en vivo.
- [x] Smoke test en vivo: `uv run python-applied-ai`, pregunta, `/stats`, `/reset`, salida.
- [x] Validación segura de `GROQ_API_KEY` sin exponer ni imprimir la clave.
- [x] Ruff, mypy y pytest pasan tras el cableado del punto de entrada.

## Comandos previstos

```bash
uv run ruff format --check .
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q
```

## Siguiente paso

Cierre del work unit: confirmar `git diff --check`, registrar el commit del slice 02-10 y continuar con la siguiente guía del curso. No se inventa contenido de guía inexistente; se sigue el orden establecido en el repositorio.

## Referencias oficiales

- Groq Python SDK: https://github.com/groq/groq-python
- Manejo de errores del SDK: https://github.com/groq/groq-python/blob/main/README.md
