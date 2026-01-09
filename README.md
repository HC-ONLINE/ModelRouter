# ModelRouter

**API HTTP asíncrona con streaming** que orquesta múltiples proveedores de LLM (Groq, OpenRouter, etc) con fallback automático, rate limiting y observabilidad completa.

[![CI/CD](https://github.com/HC-ONLINE/ModelRouter/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/HC-ONLINE/ModelRouter/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

---

## Características

**Orquestación multi-proveedor** con fallback automático (Groq → OpenRouter → Ollama)  
 **Soporte para Ollama** (modelos locales) además de proveedores cloud  
 **Streaming SSE** (Server-Sent Events) para respuestas en tiempo real  
 **Arquitectura por capas** (Controllers → Orchestrator → Router → Adapters)  
 **Rate limiting** y control de concurrencia con Redis  
 **Blacklist temporal** con backoff exponencial ante fallos  
 **Métricas Prometheus** + logs estructurados JSON  
 **Tests unitarios** con >80% cobertura  
 **Contenerización Docker** + docker-compose  
 **CI/CD con GitHub Actions**  

---

## Arquitectura

```text
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI (HTTP Layer)                    │
│                   /chat  /stream  /health                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    Controllers                              │
│  • Validación de entrada (Pydantic)                         │
│  • Autorización (API Key)                                   │
│  • Manejo de SSE                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Orchestrator                              │
│  • Timeout global de operación                              │
│  • Coordinación de streaming                                │
│  • Manejo de cancelación                                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                      Router                                 │
│  • Selección de proveedor                                   │
│  • Fallback automático                                      │
│  • Blacklist + backoff exponencial                          │
│  • Estado en Redis                                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┬─────────────────┐
        │                           │                 │
┌───────▼────────┐         ┌────────▼───────┐    ┌────▼────────┐
│  GroqAdapter   │         │ OpenRouter     │    │   Ollama    │
│                │         │    Adapter     │    │   Adapter   │
│  • Traducción  │         │  • Traducción  │    │ • Modelos   │
│    de request  │         │    de request  │    │   locales   │
│  • Stream SSE  │         │  • Stream SSE  │    │ • Stream    │
└───────┬────────┘         └────────┬───────┘    └─────┬───────┘
        │                           │                  │
        └─────────────┬─────────────┴──────────────────┘
                      │
              ┌───────▼────────┐
              │  HTTPClient    │
              │   (httpx)      │
              └────────────────┘

┌──────────────────────────────────────────────────┐
│             Infraestructura                      │
│  • Redis: blacklist, rate limits, locks          │
│  • Prometheus: métricas                          │
│  • Logs: JSON estructurado                       │
└──────────────────────────────────────────────────┘
```

---

## Inicio Rápido

### Prerrequisitos

- **Python 3.11+**
- **Docker** y **Docker Compose**
- **Redis** (incluido en docker-compose)
- Claves API de **Groq** y/o **OpenRouter**
- **Ollama** instalado localmente (opcional, para usar modelos locales)

### 1. Clonar repositorio

```bash
git clone https://github.com/HC-ONLINE/ModelRouter.git
cd ModelRouter
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita [.env](.env) y añade tus claves API:

```env
GROQ_API_KEY=tu_clave_groq
OPENROUTER_API_KEY=tu_clave_openrouter
OLLAMA_API_KEY=tu_clave_ollama
API_KEY=tu_clave_para_clientes
```

### 3. Ejecutar con Docker Compose

```bash
docker-compose up --build
```

La API estará disponible en `http://localhost:8000`

### 4. Verificar funcionamiento

```bash
# Health check
curl http://localhost:8000/health

# Métricas Prometheus
curl http://localhost:8000/metrics
```

---

## Uso de la API

### Autenticación

Incluye tu API key en el header `Authorization`:

```bash
Authorization: Bearer tu_api_key
```

### Endpoint `/chat` (no streaming)

**Request:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "¿Qué es FastAPI?"}
    ],
    "max_tokens": 200,
    "temperature": 0.7
  }'
```

**Response:**

```json
{
  "text": "FastAPI es un framework web moderno...",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "provider_meta": {
    "tokens_total": 45,
    "tokens_prompt": 10,
    "tokens_completion": 35
  }
}
```

### Endpoint `/stream` (streaming SSE)

**Request:**

```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Authorization: Bearer tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explica qué es Redis"}
    ],
    "max_tokens": 300,
    "temperature": 0.5
  }'
```

**Response (SSE):**

```text
data: Redis
data:  es
data:  una
data:  base
data:  de
data:  datos
data: ...
data: [DONE]
```

### Ejemplo Python

```python
import httpx
import json

async def stream_chat():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            'POST',
            'http://localhost:8000/stream',
            headers={
                'Authorization': 'Bearer tu_api_key',
                'Content-Type': 'application/json'
            },
            json={
                'messages': [{'role': 'user', 'content': '¿Qué es Docker?'}],
                'max_tokens': 200
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    chunk = line[6:]
                    if chunk == '[DONE]':
                        break
                    print(chunk, end='', flush=True)

# Ejecutar
import asyncio
asyncio.run(stream_chat())
```

---

## Desarrollo Local

### Instalación sin Docker

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Levantar Redis (necesario)
docker run -d -p 6379:6379 redis:7-alpine

# Ejecutar aplicación
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Ejecutar tests

```bash
# Todos los tests con cobertura
pytest --cov=app --cov-report=html

# Tests específicos
pytest tests/test_router.py -v

# Con script de utilidad
python scripts/test.py test
```

### Lint y formato

```bash
# Formatear código
black app/ tests/

# Linting
flake8 app/ tests/ --max-line-length=100

# Type checking
mypy app/ --ignore-missing-imports

# Todo junto
python scripts/test.py lint
```

---

## Observabilidad

### Métricas Prometheus

Endpoint: `http://localhost:8000/metrics`

**Métricas clave:**

- `modelrouter_requests_total{route,method,status}` - Total de requests
- `modelrouter_request_latency_seconds{route}` - Latencia por endpoint
- `modelrouter_provider_failures_total{provider,reason}` - Fallos por proveedor
- `modelrouter_provider_success_total{provider}` - Éxitos por proveedor
- `modelrouter_active_streams` - Streams activos actuales

### Logs Estructurados

Todos los logs están en formato JSON:

```json
{
  "timestamp": "2025-12-29T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.router",
  "message": "Proveedor groq emitió primer chunk",
  "request_id": "abc-123-def",
  "provider": "groq"
}
```

---

## Configuración

Todas las configuraciones están en [app/config.py](app/config.py) y se pueden sobrescribir con variables de entorno:

| Variable                         | Descripción                          | Por defecto                  |
|----------------------------------|--------------------------------------|------------------------------|
| `GROQ_API_KEY`                   | Clave API de Groq                    | -                            |
| `OPENROUTER_API_KEY`             | Clave API de OpenRouter              | -                            |
| `OLLAMA_API_KEY`                 | Clave API de Ollama (opcional)       | -                            |
| `OLLAMA_BASE_URL`                | URL de Ollama                        | `http://localhost:11434`     |
| `API_KEY`                        | Clave para autenticar clientes       | -                            |
| `REDIS_URL`                      | URL de conexión Redis                | `redis://localhost:6379/0`   |
| `PROVIDER_TIMEOUT`               | Timeout por proveedor (s)            | `30.0`                       |
| `FIRST_CHUNK_TIMEOUT`            | Timeout primer chunk streaming (s)   | `3.0`                        |
| `MAX_OPERATION_TIMEOUT`          | Timeout global operación (s)         | `120.0`                      |
| `BACKOFF_BASE_SECONDS`           | Backoff base exponencial             | `5`                          |
| `BACKOFF_MAX_SECONDS`            | Backoff máximo                       | `300`                        |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Rate limit global por minuto         | `60`                         |
| `GROQ_RATE_LIMIT`                | Rate limit específico Groq (req/min) | `30`                         |
| `OPENROUTER_RATE_LIMIT`          | Rate limit OpenRouter (req/min)      | `20`                         |
| `OLLAMA_RATE_LIMIT`              | Rate limit Ollama (req/min)          | `100`                        |
| `OPENROUTER_RATE_LIMIT`          | Rate limit OpenRouter (req/min)      | Usa límite global            |
| `MAX_CONCURRENT_STREAMS`         | Streams concurrentes máx.            | `10`                         |

### Rate Limiting por Proveedor

El sistema permite configurar límites de requests independientes para cada proveedor.
Si no se especifica un límite específico, se usa el límite global definido en
`RATE_LIMIT_REQUESTS_PER_MINUTE`.

**Ejemplo de configuración:**

```env
# Límite global (fallback)
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Límites específicos por proveedor (opcional)
# Útil para planes o límites conocidos del proveedor
GROQ_RATE_LIMIT=30
OPENROUTER_RATE_LIMIT=20
```

---

## Tests

La suite de tests incluye:

- **Tests unitarios** para Router, Orchestrator, Adapters
- **Tests de integración** para endpoints HTTP
- **Mocks** de Redis y HTTPClient

```bash
# Ejecutar tests
pytest -v

# Con cobertura
pytest --cov=app --cov-report=html

# Ver reporte HTML
open htmlcov/index.html
```

---

## Seguridad

### Importante

- **No subas claves API** al repositorio
- **Usa variables de entorno** para secrets
- **Valida rate limits** según tu plan con cada proveedor
- **Filtra contenido sensible** antes de loggear

---

## Estructura del Proyecto

```text
ModelRouter/
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app principal
│   ├── config.py               # Configuración (Settings)
│   ├── schemas.py              # Modelos Pydantic
│   ├── utils.py                # Logging, helpers
│   ├── router.py               # Router (selección/fallback)
│   ├── orchestrator.py         # Orchestrator (coordinación)
│   ├── metrics.py              # Métricas Prometheus
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── chat.py             # Endpoints /chat, /stream
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py             # ProviderAdapter abstracto
│   │   ├── groq_adapter.py     # Adapter Groq
│   │   └── openrouter_adapter.py
│   └── infra/
│       ├── __init__.py
│       ├── http_client.py      # Cliente HTTP (httpx)
│       └── redis_client.py     # Cliente Redis
├── tests/
│   ├── __init__.py
│   ├── test_router.py
│   ├── test_orchestrator.py
│   ├── test_adapters.py
│   └── test_endpoints.py
├── scripts/
│   └── test.py                 # Script utilidad tests
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI/CD
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

---

## Roadmap

### Completado

- [x] Scaffold proyecto + Docker
- [x] Adapters Groq, OpenRouter y Ollama
- [x] Router con fallback
- [x] Orchestrator
- [x] Endpoints /chat y /stream
- [x] Métricas y logging
- [x] Tests unitarios
- [x] CI/CD
- [x] Rate Limiting por proveedor

### Próximos pasos

- [ ] Permitir especificar de forma opcional un proveedor en la request
- [ ] Selección Explícita de Modelo por Proveedor
- [ ] Persistencia de historiales (PostgreSQL)
- [ ] Soporte para más proveedores (Anthropic, OpenAI)
- [ ] Cacheo de respuestas frecuentes
- [ ] Dashboard Grafana pre-configurado

---

## Licencia

Este proyecto está bajo la Licencia Apache-2.0 (Apache License 2.0). Ver [LICENSE](LICENSE) para más detalles.

---

## Disclaimer Legal

Este proyecto es para **uso personal**. Asegúrate de:

- Leer y cumplir los **Terms of Service** de los proveedores usados
- No usar rotación de proveedores para **evadir límites** de uso
- Respetar **rate limits** y políticas de cada proveedor
- No almacenar/procesar datos sensibles sin las medidas de seguridad apropiadas

**El autor no se hace responsable del uso indebido de esta herramienta.**

---

## Hecho con ❤️ por HC-ONLINE

⭐ **Si te resulta útil, deja una estrella en GitHub** ⭐
