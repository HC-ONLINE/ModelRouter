"""
Métricas Prometheus para observabilidad.
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Response


# ========== Contadores ==========

# Requests totales por endpoint y método
request_total = Counter(
    "modelrouter_requests_total",
    "Total de requests recibidas",
    ["route", "method", "status"],
)

# Fallos de proveedores
provider_failures_total = Counter(
    "modelrouter_provider_failures_total",
    "Total de fallos por proveedor",
    ["provider", "reason"],
)

# Éxitos de proveedores
provider_success_total = Counter(
    "modelrouter_provider_success_total",
    "Total de generaciones exitosas por proveedor",
    ["provider"],
)


# ========== Histogramas ==========

# Latencia de requests
request_latency_seconds = Histogram(
    "modelrouter_request_latency_seconds",
    "Latencia de requests en segundos",
    ["route"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

# Tokens generados (si disponible)
tokens_generated = Histogram(
    "modelrouter_tokens_generated",
    "Tokens generados por request",
    ["provider"],
    buckets=(10, 50, 100, 250, 500, 1000, 2000, 4000),
)


# ========== Gauges ==========

# Streams activos
active_streams = Gauge(
    "modelrouter_active_streams", "Número de streams activos actualmente"
)

# Proveedores blacklisted
providers_blacklisted = Gauge(
    "modelrouter_providers_blacklisted",
    "Número de proveedores en blacklist",
    ["provider"],
)


# ========== Funciones de ayuda ==========


def record_request(route: str, method: str, status: int) -> None:
    """Registra una request."""
    request_total.labels(route=route, method=method, status=status).inc()


def record_provider_failure(provider: str, reason: str) -> None:
    """Registra un fallo de proveedor."""
    provider_failures_total.labels(provider=provider, reason=reason).inc()


def record_provider_success(provider: str) -> None:
    """Registra un éxito de proveedor."""
    provider_success_total.labels(provider=provider).inc()


def record_latency(route: str, duration: float) -> None:
    """Registra latencia de una request."""
    request_latency_seconds.labels(route=route).observe(duration)


def record_tokens(provider: str, token_count: int) -> None:
    """Registra tokens generados."""
    tokens_generated.labels(provider=provider).observe(token_count)


def increment_active_streams() -> None:
    """Incrementa contador de streams activos."""
    active_streams.inc()


def decrement_active_streams() -> None:
    """Decrementa contador de streams activos."""
    active_streams.dec()


def set_provider_blacklisted(provider: str, is_blacklisted: bool) -> None:
    """Actualiza estado de blacklist de proveedor."""
    providers_blacklisted.labels(provider=provider).set(1 if is_blacklisted else 0)


# ========== Endpoint de métricas ==========


def get_metrics() -> Response:
    """
    Genera respuesta con métricas en formato Prometheus.

    Returns:
        Response con métricas
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
