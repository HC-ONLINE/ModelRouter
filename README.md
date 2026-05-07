# ModelRouter

**Asynchronous HTTP API with streaming** that orchestrates multiple LLM providers with automatic fallback and observability.

[![CI/CD](https://github.com/HC-ONLINE/ModelRouter/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/HC-ONLINE/ModelRouter/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

---

## Main Features

- **Multi-provider Orchestration:** Automatic fallback between:
  - Groq
  - OpenRouter
  - OpenAI
  - Ollama
- **Native Streaming:** Support for Server-Sent Events (SSE).
- **Resilience:** Rate limiting, temporary blocklisting, and exponential backoff.
- **Production Ready:** Includes Prometheus metrics, structured logging, and Docker deployment.

---

## Quick Start (Docker)

### 1. Configuration

```bash
git clone https://github.com/HC-ONLINE/ModelRouter.git
cd ModelRouter
cp .env.example .env
```

Edit the `.env` file with your API keys.

---

### 2. Deployment

```bash
docker-compose up --build
```

The API will be available at <http://localhost:8000>.

---

### Basic Usage

#### Chat (Non-Streaming)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}], "provider": "groq"}'
```

---

#### Streaming

```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Authorization: Bearer your_api_key" \
  -d '{"messages": [{"role": "user", "content": "Tell a story"}]}'
```

---

### Detailed Documentation

- [Architecture](docs/architecture.md) - How it works internally.
- [Configuration](docs/configuration.md) - Environment variables and rate limits.
- [Usage Examples](docs/examples.md) - Examples using `curl` and `fetch`.
- [Development](docs/development.md) - Contribution guide, tests and linting.
- [Observability](docs/observability.md) - Metrics and logs.
- [Security](docs/security.md) - Security and legal notes.

These documents are located in the `docs/` folder.

---

### Project Structure

```plaintext
ModelRouter/
├── api/                # Core logic (FastAPI, Router, Orchestrator)
├── api/providers/      # Adapters (Groq, OpenRouter, Ollama)
├── api/infra/          # HTTP clients and Redis integrations
├── tests/              # Test suite
├── docs/               # Technical documentation
└── docker-compose.yml
```

---

## License

This project is licensed under the Apache-2.0 License. See [LICENSE](LICENSE) for details.

---

## Legal Disclaimer

This project is intended for individual or self-hosted use. Make sure to:

- Read and comply with the **Terms of Service** of the providers you use
- Do not use provider rotation to **evade usage limits**
- Respect rate limits and policies of each provider
- Do not store/process sensitive data without appropriate security measures

**The author assumes no liability for misuse of this software.**

---

## Community

Made with ❤️ by HC-ONLINE. See [ROADMAP.md](ROADMAP.md) for next steps

⭐ **If you find it useful, please give it a star on GitHub** ⭐
