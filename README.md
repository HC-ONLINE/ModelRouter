# ModelRouter

**API HTTP asíncrona con streaming** que orquesta múltiples proveedores de LLM (Groq, OpenRouter y Ollama) con fallback automático y observabilidad.

[![CI/CD](https://github.com/HC-ONLINE/ModelRouter/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/HC-ONLINE/ModelRouter/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

---

## Características Principales

* **Orquestación Multi-proveedor:** Fallback automático entre Groq, OpenRouter y Ollama.
* **Streaming Nativo:** Soporte para Server-Sent Events (SSE).
* **Resiliencia:** Rate limiting, blacklist temporal y backoff exponencial.
* **Production Ready:** Métricas Prometheus, logs estructurados y Dockerizado.

---

## Inicio Rápido (Docker)

### 1. Configuración

```bash
git clone https://github.com/HC-ONLINE/ModelRouter.git
cd ModelRouter
cp .env.example .env
```

Edita el archivo .env con tus claves API.

---

### 2. Despliegue

```bash
docker-compose up --build
```

La API estará lista en <http://localhost:8000>.

---

### Uso Básico

#### Chat (No-Streaming)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hola"}], "provider": "groq"}'
```

---

#### Streaming

```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Authorization: Bearer tu_api_key" \
  -d '{"messages": [{"role": "user", "content": "Cuenta un cuento"}]}'
```

---

### Documentación Detallada

* [Arquitectura](docs/architecture.md) - Cómo funciona internamente.
* [Configuración](docs/configuration.md) - Variables de entorno y rate limits.
* [Desarrollo](docs/development.md) - Guía para contribuir, tests y linting.
* [Observabilidad](docs/observability.md) - Métricas y Logs.
* [Seguridad](docs/security.md) - Notas de seguridad y legal.
Estos documentos están en la carpeta `docs/`.

---

### Estructura del Proyecto

```plaintext
ModelRouter/
├── api/                # Lógica central (FastAPI, Router, Orchestrator)
├── api/providers/      # Adapters (Groq, OpenRouter, Ollama)
├── api/infra/          # Clientes HTTP y Redis
├── tests/              # Suite de pruebas
├── docs/               # Documentación técnica
└── docker-compose.yml
```

---

## Licencia

Este proyecto está bajo la Licencia Apache-2.0 (Apache License 2.0). Ver [LICENSE](LICENSE) para más detalles.

---

## Disclaimer Legal

Este proyecto es para **uso personal**. Asegúrate de:

* Leer y cumplir los **Terms of Service** de los proveedores usados
* No usar rotación de proveedores para **evadir límites** de uso
* Respetar **rate limits** y políticas de cada proveedor
* No almacenar/procesar datos sensibles sin las medidas de seguridad apropiadas

**El autor no se hace responsable del uso indebido de esta herramienta.**

---

## Hecho con ❤️ por HC-ONLINE. Ver [ROADMAP.md](ROADMAP.md) para próximos pasos

⭐ **Si te resulta útil, deja una estrella en GitHub** ⭐
