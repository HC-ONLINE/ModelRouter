# Desarrollo local

Guía rápida para contribución y desarrollo local.

## Entorno recomendado

- Python 3.11+
- Virtualenv

## Pasos rápidos

```bash
# Crear entorno virtual
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Unix
source .venv/bin/activate
# Instalar dependencias

pip install -r requirements.txt
# o
pip install -r requirements-dev.txt

# Levantar Redis para desarrollo
docker run -d -p 6379:6379 redis:7-alpine

# Ejecutar la app

uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
# Ejecutar todos los tests
pytest -v

# Tests específicos
pytest tests/test_router.py -v
```

## Formato y lint

```bash
# Formatear
black .
# Lint
flake8 . --max-line-length=100
# Type check
mypy . --ignore-missing-imports
```

## Notas

- Use `scripts/test.py` para utilidades comunes (lint, tests).
