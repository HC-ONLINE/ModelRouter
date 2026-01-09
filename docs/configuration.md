# Configuración

Listado de variables relevantes y su propósito. Para la configuración completa revisa `api/config.py`.

## Variables críticas (mínimo)

- `API_KEY` — clave para clientes que consumen la API
- `REDIS_URL` — conexión a Redis (ej. `redis://localhost:6379/0`)
- `OLLAMA_BASE_URL` — URL base de Ollama (ej. `http://host.docker.internal:11434` cuando se ejecuta con Docker)
- `GROQ_API_KEY` — clave para Groq (si se usa)
- `OPENROUTER_API_KEY` — clave para OpenRouter (si se usa)

## Variables ampliadas

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
| `MAX_CONCURRENT_STREAMS`         | Streams concurrentes máx.            | `10`                         |

## Notas operativas

- Cuando ModelRouter corre dentro de Docker y Ollama corre en el host, use `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- No subir claves a repositorios públicos.
- Para entornos de producción usar un secreto manager (Vault/Secret Manager).
