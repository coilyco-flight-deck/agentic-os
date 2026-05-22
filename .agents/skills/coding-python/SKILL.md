---
name: coding-python
description: Python umbrella skill. Kai's primary language, 10+ years of practice. Modern Python defaults (3.12+, type hints, ruff for lint, uv for env management, pytest). Triggers - python, python3, .py, pip, uv, poetry, pyenv, pytest, ruff, mypy, pyright, asyncio, pydantic, typing, dataclass, fastapi, flask, django.
---

# coding-python

Umbrella skill for any Python work. Triggers on the broad Python keyword surface. Refine details over time as patterns crystallize.

## Defaults

- **Version**: 3.12+ unless a target environment pins lower. Reach for the newest features Kai can use.
- **Env management**: `uv` (Astral). Not pip/venv directly, not poetry. `uv venv`, `uv pip install`, `uv run`.
- **Lint/format**: `ruff` for both. Single tool, fast, opinionated.
- **Type checking**: `pyright` or `mypy`. Type hints expected on new code, not retrofitted on legacy aggressively.
- **Tests**: `pytest`. Async tests via `pytest-asyncio` or `anyio`.
- **Formatting**: ruff format (replaces black). Line length 100 unless project pins otherwise.

## Style

- Type hints on function signatures, less religious about every local variable.
- Dataclasses or pydantic over dict-shaped objects when the shape is known.
- f-strings over `.format()` or `%`. Always.
- `pathlib.Path` over `os.path` string surgery.
- Async-first when there's I/O. Sync only when nothing benefits from concurrency.
- Stdlib first when reasonable. Reach for deps when they earn it.

## When this skill is active

Kai is editing or writing Python. Inherit her preferences before reaching for general Python knowledge from training data.
