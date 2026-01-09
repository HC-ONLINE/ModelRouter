# Observabilidad

Este documento recopila las métricas y prácticas de logging usadas por ModelRouter.

## Métricas (Prometheus)

Métricas principales expuestas en `/metrics`:

- `modelrouter_requests_total{route,method,status}` - Total de requests
- `modelrouter_request_latency_seconds{route}` - Latencia por endpoint
- `modelrouter_provider_failures_total{provider,reason}` - Fallos por proveedor
- `modelrouter_provider_success_total{provider}` - Éxitos por proveedor
- `modelrouter_active_streams` - Streams activos actuales

Ejemplo de scraping en Prometheus: añade `http://<host>:8000/metrics` como target.

## Logs

Los logs se emiten en formato JSON estructurado. Campos relevantes:

- `timestamp` - ISO8601
- `level` - INFO / WARNING / ERROR
- `logger` - nombre del logger (ej. `api.router`)
- `message` - mensaje principal
- `request_id` - ID correlacionado por request
- `provider` - proveedor implicado (cuando aplica)

Ejemplo de log:

```json
{
  "timestamp": "2026-01-09T10:30:45.123Z",
  "level": "INFO",
  "logger": "api.router",
  "message": "Proveedor groq emitió primer chunk",
  "request_id": "abc-123-def",
  "provider": "groq"
}
```

## Recomendaciones

- En producción, enviar logs a un agregador (ELK/Datadog/CloudWatch).
- Scrapear `/metrics` con Prometheus y montar dashboards en Grafana.
- Activar alertas en errores de proveedor y latencias altas.
