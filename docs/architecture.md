# Arquitectura de ModelRouter

ModelRouter utiliza una arquitectura por capas diseñada para la extensibilidad y la resiliencia en entornos asíncronos.

## Diagrama de Componentes

```plaintext
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI (HTTP Layer)                    │
│                   /chat  /stream  /health                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    Controllers                              │
│  • Validación (Pydantic) | Autorización | Manejo SSE        │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Orchestrator                              │
│  • Timeouts globales | Coordinación | Cancelación           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                      Router                                 │
│  • Selección | Fallback | Blacklist | Estado en Redis       │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┬─────────────────┐
┌───────▼────────┐         ┌────────▼───────┐    ┌────▼────────┐
│   GroqAdapter  │         │   OpenRouter   │    │   Ollama    │
└───────┬────────┘         └────────┬───────┘    └─────┬───────┘
        └─────────────┬─────────────┴──────────────────┘
              ┌───────▼────────┐
              │   HTTPClient   │
              └────────────────┘
```

---

## Flujo de una Petición

1. El cliente envía una petición HTTP a FastAPI (endpoint `/chat` o `/stream`).

2. El Controller: Valida la API Key y el esquema del mensaje.

3. El Orchestrator: Inicia un timer global. Si el proveedor principal falla o tarda demasiado, instruye al Router para buscar el siguiente.

4. El Router: Verifica en Redis si el proveedor está en "blacklist" por errores recientes.

5. El Adapter: Traduce el formato estándar de ModelRouter al formato específico del SDK/API del proveedor (Groq, OpenAI, etc).
