# Desarrollo local

Guía rápida para contribución y desarrollo local.

## Entorno recomendado

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gestor de entornos y dependencias)

## Pasos rápidos

```bash
# Crear .venv e instalar dependencias (uv gestiona el entorno)
uv sync --all-extras

# Levantar Redis para desarrollo
docker run -d -p 6379:6379 redis:7-alpine

# Ejecutar la app
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
# Ejecutar todos los tests
uv run pytest -v

# Tests específicos
uv run pytest tests/test_router.py -v
```

## Formato y lint

```bash
# Formatear
uv run black .
# Lint
uv run flake8 . --max-line-length=100
# Type check
uv run mypy . --ignore-missing-imports
```

## Notas

- Use `uv run scripts/test.py` para utilidades comunes (lint, tests).
