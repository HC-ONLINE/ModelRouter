# Ejemplos de uso

Ejemplos rápidos para probar la API de ModelRouter con `curl` y `fetch` (browser / Node).

Sustituye `tu_api_key` por el valor en tu `.env`.

---

## 1) `curl` — petición sencilla `/chat` (no-stream)

Ejemplo en una sola línea (Bash/PowerShell):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "¿Cuál es la capital de Francia?"}], "max_tokens": 50}'
```

Usando archivo `body.json` (recomendado para payloads complejos):

`body.json`

```json
{
  "messages": [{"role": "user", "content": "¿Cuál es la capital de Francia?"}],
  "max_tokens": 50,
  "provider": "ollama"
}
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer tu_api_key" \
  -H "Content-Type: application/json" \
  -d @body.json
```

---

## 2) `curl` — streaming SSE `/stream`

Recibe chunks en tiempo real con `-N`:

```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Authorization: Bearer tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Cuenta un cuento corto"}], "max_tokens":150}'
```

Verás líneas `data: <chunk>` hasta `data: [DONE]`.

---

## 3) `fetch` en Browser — petición no-stream (JSON)

```javascript
// Browser (fetch)
async function chat() {
  const resp = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer tu_api_key',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      messages: [{ role: 'user', content: '¿Qué es FastAPI?' }],
      max_tokens: 100
    })
  });

  const data = await resp.json();
  console.log(data);
}

chat();
```

---

## 4) `fetch` en Browser — streaming con `ReadableStream`

El estándar `EventSource` en navegadores no soporta nativamente `POST` ni el envío de cabeceras personalizadas (por ejemplo `Authorization`). Para recibir streaming SSE/NDJSON desde el navegador usa `fetch` y consume la `ReadableStream` de la respuesta — es equivalente al Ejemplo 6 (Node).

```javascript
// Browser — streaming con fetch y ReadableStream
async function streamChat() {
  const res = await fetch('http://localhost:8000/stream', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer tu_api_key',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ messages: [{ role: 'user', content: 'Cuenta un cuento corto' }], max_tokens: 150 })
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let done = false;
  while (!done) {
    const { value, done: d } = await reader.read();
    done = d;
    if (value) {
      const text = decoder.decode(value, { stream: true });
      console.log('chunk:', text);
      if (text.includes('[DONE]')) break;
    }
  }
}

streamChat().catch(console.error);
```

> Nota: cuando uses `fetch` desde el navegador asegúrate de que el backend tenga CORS habilitado para aceptar `Authorization` y `Content-Type` desde el origen del cliente, o utiliza un proxy que agregue las cabeceras necesarias.

---

## 5) `node-fetch` (Node.js) — no-stream

```javascript
// Node 18+ (global fetch) o con node-fetch
import fetch from 'node-fetch'; // si tu Node no tiene fetch

async function chatNode() {
  const res = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer tu_api_key',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ messages: [{ role: 'user', content: 'Hola' }], max_tokens: 80 })
  });
  console.log(await res.json());
}

chatNode();
```

---

## 6) `fetch` en Node — consumir streaming (Readables)

```javascript
// Node 18+ ejemplo de streaming con fetch y ReadableStream
const res = await fetch('http://localhost:8000/stream', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer tu_api_key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ messages: [{ role: 'user', content: 'Cuenta un chiste' }], max_tokens: 150 })
});

const reader = res.body.getReader();
const decoder = new TextDecoder();
let done = false;
while (!done) {
  const { value, done: d } = await reader.read();
  done = d;
  if (value) {
    const text = decoder.decode(value);
    process.stdout.write(text);
  }
}
```

---

## Notas

- La API acepta el campo `provider` en el cuerpo de la petición (opcional). Si se especifica, ModelRouter intentará usar únicamente ese proveedor; si no, aplicará la lógica de rotación y fallback.

- Para pruebas locales con Docker, si `ModelRouter` corre dentro de un contenedor y `Ollama` en el host, configura `OLLAMA_BASE_URL=http://host.docker.internal:11434`.

- Usa `body.json` para payloads largos o que contengan saltos de línea para evitar problemas de escape en shells.

- Reemplaza `tu_api_key` por el valor real en `.env` o usa el header correcto según tu entorno.
