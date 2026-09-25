# Imagen base con Python 3.11 (Alpine es más ligera y segura)
FROM python:3.11-slim-bookworm AS builder

# uv reemplaza pip para instalar dependencias (misma herramienta que local y CI)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Directorio de trabajo; la etapa runtime usa la misma ruta para que las
# rutas absolutas registradas dentro de .venv sigan siendo válidas
WORKDIR /app

# Actualizar paquetes del sistema para parches de seguridad
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar pyproject + uv.lock e instalar dependencias primero (cache de capas)
# README.md es requerido por los metadatos de pyproject.toml
COPY pyproject.toml uv.lock README.md ./
RUN UV_PYTHON_DOWNLOADS=never uv sync --locked --no-install-project

# Copiar código fuente e instalar el proyecto
COPY api/ ./api/
RUN UV_PYTHON_DOWNLOADS=never uv sync --locked

# Stage 2: Runtime
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copiar el .venv construido en el builder (misma ruta absoluta)
COPY --from=builder /app/.venv /app/.venv

# Copiar código fuente
COPY api/ ./api/

# Crear usuario no-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=2.0)" || exit 1

# Comando para ejecutar la aplicación
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
