# Cuenta de GroqCloud y API key configuradas de forma segura

> **Aviso de derechos y privacidad:** Este documento es una nota de estudio independiente que resume objetivos de aprendizaje y decisiones originales de implementación. No reproduce transcripciones de cursos de pago ni material con derechos de autor. No incluye claves de API reales, datos personales ni activos de video.

## Estado

**Completed** — la cuenta del Free Plan, la API key y el archivo `.env` ya están configurados y verificados.

## Objetivo de aprendizaje

Obtener y almacenar una API key de GroqCloud de forma segura, y comprender los conceptos de límites de uso y costos sin depender de OpenAI.

## Ruta rápida

1. Iniciar sesión o registrarse en `https://console.groq.com`.
2. Crear una API key en `https://console.groq.com/keys` con un nombre descriptivo y copiarla una sola vez.
3. Guardar la key en `.env` (variable `GROQ_API_KEY`).
4. Confirmar que Git la ignora: `git check-ignore -v .env`.
5. (Verificación de la llamada) continuar con `02-04-first-groq-api-call.md`.

## Resumen del concepto del instructor

La lección original "Obtener API key / costos" del curso cubre: registro en la consola del proveedor, creación de organización y proyecto, generación de la API key (el secreto solo se muestra una vez), almacenamiento en variables de entorno, método de pago, glosario de límites de uso, costo por token y controles de protección de gasto. Esta nota conserva esos objetivos y los aplica a GroqCloud. No se reproduce el texto del curso.

## Nuestra adaptación Groq y tabla de mapeo

| Concepto (OpenAI original) | Adaptación Groq |
| --- | --- |
| Cuenta en `platform.openai.com` | Cuenta en `console.groq.com` |
| API key de OpenAI (`OPENAI_API_KEY`) | API key de GroqCloud (`GROQ_API_KEY` no aplica; se usa `GROQ_API_KEY` como variable del proyecto) |
| Modelo por defecto `gpt-*` | `openai/gpt-oss-20b` |
| Explicación de costos OpenAI | Explicación de costos/límites de Groq |

## Crear, copiar, guardar, revocar y rotar la API key

1. Ir a `https://console.groq.com/keys` y crear una key con un nombre descriptivo (por ejemplo `python-applied-ai-devtalles-s2`).
2. **Copiar la key inmediatamente**: Groq la muestra completa solo una vez. Si se pierde, debe revocarse y crearse otra.
3. **Guardar en `.env`**, nunca en el código ni en el historial de comandos.
4. **Revocar/rotar**: desde `/keys` puede eliminar (revoke) una key. Si sospecha exposición, revóquela al instante y genere una nueva; actualice `.env`.

## Free Plan frente a nivel de pago (conceptos)

- **Free Plan**: permite usar ciertos modelos con límites gratuitos por modelo. Para la práctica del curso basta el Free Plan; no se requiere tarjeta ni acción de pago.
- **Nivel de pago (Developer)**: los precios se basan en consumo facturable (tokens). Los valores concretos son volátiles y deben consultarse en las páginas oficiales vigentes.
- **Límites de tasa (rate limits)** se expresan como RPM (requests/min), RPD (requests/day), TPM (tokens/min) y TPD (tokens/day). Se aplican a nivel de **organización**, no por API key.
- **Ejemplo ilustrativo con fecha (2026-08-27)** para `openai/gpt-oss-20b` en Free Plan: aproximadamente 30 RPM / 1K RPD / 8K TPM / 200K TPD. El nivel Developer base mostraba ~1K RPM / 250K TPM. Estos números cambian: consulte siempre `https://console.groq.com/settings/limits` y `https://console.groq.com/docs/models`.
- **Equivalencia de tokens (solo intuición gruesa del inglés)**: ~1 token ≈ 0.75 palabras es una heurística aproximada; el español y cada tokenizador difieren. Úsela solo para una intuición cualitativa, **nunca** para facturación ni para fijar límites duros.

## Controles de gasto como principio atemporal

En niveles de pago, fije un límite de gasto (spend limit / budget cap) como protección ante bucles, errores o picos. Si sospecha uso anómalo, revoque y rote la key. No se afirma una ubicación concreta de la interfaz de Groq ni una etiqueta específica; en niveles de pago guíese por la documentación oficial `/docs/spend-limits` y las secciones de facturación vigentes. El Free Plan no requiere ninguna acción de pago.

## Archivos de entorno: `.env.example` y `.env`

`.env.example` (rastreado, sin secretos — placeholder vacío):

```text
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=
```

`.env` (privado, ignorado por Git — no commitee nunca; pegue la key real después de `GROQ_API_KEY=`):

```text
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=
```

Nunca escriba la key real en `.env.example`, nunca la imprima y nunca la registre en logs.

## Comprobaciones seguras (sin exponer la key)

Verifique que `.env` está ignorado:

```bash
git check-ignore -v .env
```

El formato de salida es `<fuente>:<línea>:<patrón> <ruta>`; el último token es la ruta evaluada, **no** una entrada duplicada. Por ejemplo, una línea como `.gitignore:7:.env .env` es salida normal, no duplicados.

**Prohibido**: `cat .env` (expone la key en pantalla), añadir `.env` a un commit, o pegarlo en issues/chat. Para validar la presencia de la key de forma segura, use el smoke test del siguiente documento (que la lee vía el objeto `Settings` y no la imprime). No se fíe de comprobar `os.environ`: cargar `.env` con `pydantic-settings` **no** exporta las variables al entorno del proceso.

## Estado actual

- Cuenta Groq Free Plan, API key y `.env` ya completos y verificados.
- `git check-ignore -v .env` confirma que `.env` está ignorado.
- `.env.example` commiteado con `GROQ_API_KEY=` (vacío).

## Decisiones, trade-offs y errores comunes

- **Groq en lugar de OpenAI**: el proyecto ya usa Groq; se conserva el objetivo de aprendizaje de gestionar secretos y entender límites.
- **No inventar etiquetas de UI**: los textos de la consola pueden cambiar; siga el equivalente funcional en pantalla.
- **No `cat .env`**: exponer la key en scrollback es una fuga accidental; si ocurre, revoque y rote.
- **No usar `os.environ` para validar**: `pydantic-settings` no exporta a `os.environ`.

## Referencias externas oficiales

- https://console.groq.com
- https://console.groq.com/keys
- https://console.groq.com/settings/limits
- https://console.groq.com/docs/models
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/spend-limits
- https://github.com/groq/groq-python
