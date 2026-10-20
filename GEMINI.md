# llm-voice-advisor

Estado: el dominio y la estructura de `src/` están en refactor. Inspecciona el árbol real (`codegraph` o `ls`) y no asumas mapas de capas escritos. Las decisiones de arquitectura provisionales viven en Engram (`topic_key: architecture/*`).

## Comandos
- Tests: `uv run pytest`
- Integración: `uv run pytest -m integration`
- Estilo y lint: `uv run ruff format` y `uv run ruff check`
- Los guardrails de arquitectura viven en `pyproject.toml` (`[tool.ruff]`, `[tool.importlinter]`); no los dupliques aquí. Si uno estorba al refactor, propón su cambio en el PR.

## Skills Locales de Python (`.agents/skills/`)
Al trabajar en archivos de este repositorio, carga bajo demanda la skill específica según la tarea:
- Diseño y extracción de clases/funciones en Python: `python-design-patterns` y `py-complexity`
- Tipado estricto (`Protocol`, `StrEnum`, `@dataclass(frozen=True)`): `python-type-safety`
- Manejo de errores y validación: `python-error-handling`
- Estilo PEP 8, docstrings y `ruff`: `python-code-style` y `python-anti-patterns`
- Pruebas unitarias e integración con `pytest`: `python-testing-patterns`
