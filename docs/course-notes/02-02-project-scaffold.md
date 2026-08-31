# Proyecto base listo: andamiaje reproducible con uv, Python 3.13 y Groq

> **Aviso de derechos y privacidad:** Este documento es una nota de estudio independiente que resume objetivos de aprendizaje y decisiones originales de implementación. No reproduce transcripciones de cursos de pago ni material con derechos de autor. No incluye claves de API reales, datos personales ni activos de video.

## Estado

**Completed — etapa 1 de 9.** Esta guía crea únicamente el andamiaje reproducible. Parte de un repositorio clonado y termina con un paquete importable, herramientas de calidad y **1 test** de humo. No adelanta configuración de costo, temperatura, chatbot ni CLI.

## Objetivo de aprendizaje

Crear un proyecto Python reproducible, aislado y listo para integrar modelos de lenguaje por proveedor, sin hardcodear credenciales y con controles de calidad automáticos.

## Ruta rápida

1. Usar el repositorio ya clonado (no ejecutar un segundo `git init`).
2. Instalar el intérprete de proyecto: `uv python install 3.13` y `uv sync`.
3. Crear la plantilla `.env.example`; la API key se incorpora de forma segura en 02-03.
4. Ejecutar las comprobaciones: `uv run pytest`, `uv run ruff format .`, `uv run ruff check .`, `uv run mypy src`.
5. Confirmar que el test de importación está verde y continuar con 02-03.

## Resumen del concepto del instructor

La lección original "Creando proyecto" del curso propone un flujo con `venv` y `pip`:

- Crear la carpeta del proyecto y un entorno virtual con `python3 -m venv .venv`.
- Activar el entorno e instalar `openai`, `python-dotenv`, `pydantic` y `rich`.
- Crear la estructura `src/`, `data/`, `notebooks/`, `tests/`, `.env`, `.env.example`, `.gitignore` y `README.md`.
- Inicializar Git, hacer commit del andamiaje y generar `requirements.txt` con `pip freeze`.

Este resumen preserva la intención de aprendizaje; la implementación real se adapta con `uv` y Groq (ver tabla siguiente). No se reproduce el texto del curso.

## Nuestra adaptación Groq/uv y tabla de mapeo

| Concepto del instructor | Adaptación en este proyecto |
| --- | --- |
| `venv` + `pip` + `requirements.txt` | `uv` + `pyproject.toml` + `uv.lock` |
| Dependencias `openai`, `python-dotenv`, `pydantic`, `rich` | `groq`, `httpx`, `pydantic-settings`, `rich` |
| `.env` + `.env.example` manuales | `.env.example` rastreado; `.env` ignorado por Git |
| `git init` local | Repositorio ya clonado (sin segundo `git init`) |
| Python global del sistema | Python 3.13.15 gestionado por `uv`, aislado del Python global 3.14.7 |

## Pasos detallados de implementación

### Aislamiento del intérprete

- Su Python global es **3.14.7**. El proyecto fija **Python 3.13.15** mediante `uv` (`.python-version` y `requires-python = ">=3.13,<3.14"`), de modo que las dependencias se resuelven contra 3.13 sin tocar el intérprete global.

### Inicialización

```bash
uv init --package --python 3.13
```

Esto crea un paquete instalable bajo `src/`. No se ejecuta `git init` porque el repositorio ya existe y está conectado a `origin`.

### Dependencias

- Runtime: `groq`, `httpx`, `pydantic-settings`, `rich`.
- Desarrollo: `pytest`, `pytest-cov`, `ruff`, `mypy`.

### Estructura de directorios

```text
src/python_applied_ai/   # paquete de aplicación
tests/                   # pruebas automatizadas
docs/                    # notas escritas
notebooks/               # experimentos
data/public/             # muestras redistribuibles (rastreado con .gitkeep)
data/private/            # entradas locales, nunca commiteadas
data/generated/          # artefactos regenerables, nunca commiteados
```

### `.gitignore` (clave)

```text
.venv/
.env
.env.*
!.env.example
```

### `.env.example` (rastreado, sin secretos)

```text
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
LLM_MAX_TOKENS=256

GROQ_API_KEY=
GOOGLE_API_KEY=
OPENAI_API_KEY=

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:latest

```

> Esta es la fotografía de la etapa 02-02. Las tarifas se añaden en 02-05 y `LLM_TEMPERATURE` en 02-07. `.env.example` es rastreado y nunca contiene secretos; `.env` es privado e ignorado.

### Configuración de herramientas en `pyproject.toml`

- `pytest` con `testpaths = ["tests"]` y `addopts = "-q --strict-markers"`.
- `ruff` con `line-length = 100`, `target-version = "py313"` y reglas `E, F, I, B, UP`.
- `mypy` en modo `strict`, `python_version = "3.13"`.

### Prueba de humo y entrypoint

`tests/test_package.py` importa el paquete, lo que valida la instalación editable. El entrypoint se reserva como límite de composición y se conecta al chatbot completo recién en 02-10.

## Verificación y checklist

- [x] `uv run pytest -q` pasa **1 test** de importación.
- [x] `uv run ruff format .` y `uv run ruff check .` sin errores.
- [x] `uv run mypy src` sin errores (modo strict).
- [x] `git check-ignore -v .env` confirma que `.env` está ignorado.
- [x] `.env.example`, `uv.lock` y los `.gitkeep` están rastreados; `.env` y `.venv` no.
- [x] El hito histórico `e263249` representa este andamiaje.

## Nota técnica: uv, src-layout, entrypoint y archivos de entorno

- **`uv`**: gestor de proyecto y entorno que produce `uv.lock` para reproducibilidad. Comandos canónicos: `uv run pytest -q`, `uv run ruff format --check .`, `uv run ruff check src tests`, `uv run mypy src tests`. No use `pip`/`venv` directamente.
- **`src-layout`**: el paquete vive bajo `src/python_applied_ai/`. El intérprete se resuelve desde la raíz del repositorio (`uv run python -m python_applied_ai.hello_ai`), lo que hace que `.env` se cargue por el directorio de trabajo actual.
- **Entrypoint**: `pyproject.toml` expone `python-applied-ai = "python_applied_ai:main"`. El punto de entrada ejecutable se prueba con `uv run python-applied-ai`. No hay un segundo `git init`; el repositorio ya estaba clonado y conectado a `origin`.
- **`.env` vs `.env.example`**: `.env.example` es la plantilla rastreada en Git (placeholders en blanco, sin secretos). `.env` es privado, ignorado por Git (`.gitignore` contiene `.env`), y nunca se commitea. `pydantic-settings` carga `.env` directamente en `Settings`; no use `load_dotenv` ni `os.environ` para validar.
- **Verificación del scaffold**: `git check-ignore -v .env` confirma que `.env` está ignorado; `uv run pytest -q` valida que la instalación editable funciona; `uv run ruff format --check .` y `uv run ruff check .` validan formato/lint; `uv run mypy src` valida tipos strict.

- **`uv` frente a `pip`/`venv`:** mayor reproducibilidad (`uv.lock`) y un intérprete aislado, a cambio de aprender una nueva herramienta.
- **`pydantic-settings` frente a `python-dotenv` + `pydantic`:** configuración tipada y validada en un solo lugar.
- **`httpx` y `pydantic-settings`:** el nombre correcto de los paquetes es `httpx` y `pydantic-settings`; una errata como `hhttpx` provoca un fallo de instalación.
- **`.gitkeep`, no `.gitignore` vacío anidado:** para rastrear directorios vacíos se usa `.gitkeep`; no se crean `.gitignore` vacíos internos.
- **Sin secretos en archivos rastreados:** `.env` nunca se commitea; solo `.env.example` con valores en blanco.
- **Sin segundo `git init`:** el repositorio ya estaba clonado y conectado a `origin`.

## Resultado de etapa y siguiente paso

El repositorio queda importable y reproducible con 1 test. Continúe con [02-03-groq-account-api-key.md](./02-03-groq-account-api-key.md) para configurar el secreto sin exponerlo.

## Referencias externas oficiales

- Documentación de uv: https://docs.astral.sh/uv/
- pydantic-settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- groq-python: https://github.com/groq/groq-python
