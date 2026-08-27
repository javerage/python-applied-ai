# Python Applied AI

Applied AI learning portfolio: provider-neutral LLM integrations, retrieval-augmented
generation, and agentic workflows, built while studying practical applied-AI courses.

This repository is an independent learning portfolio. It is not affiliated with, endorsed by,
or derived from any paid course material, proprietary solutions, or vendor content.

## Stack

- Python 3.13 managed by [uv](https://docs.astral.sh/uv/)
- `groq` for cloud LLM access
- `httpx` for direct provider and local Ollama calls
- `pydantic-settings` for typed configuration
- `rich` for terminal rendering
- `pytest`, `ruff`, and `mypy` for quality


## Setup

```bash
uv python install 3.13
uv sync
cp .env.example .env
```

Edit .env and add your provider keys. .env is ignored by Git.

## Quality
```bash
uv run pytest
uv run ruff format .
uv run ruff check
uv run mypy src
```

## Layout
- src/python_applied_ai: application package
- tests: automated tests
- docs: written notes
- notebooks: experiments
- data/public: redistributable samples
- data/private: local inputs, never committed
- data/generated: regenerable artifacts, never committed
