"""
Aplicación principal FastAPI.
Inicializa dependencias, configura middleware y define routes.
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator, Sequence
from typing import cast, Any
import logging
import time

from api.config import settings
from api.utils import setup_logging
from api.infra.http_client import create_http_client
from api.infra.redis_client import create_redis_client
from api.providers.base import ProviderAdapter
from api.providers.groq_adapter import GroqAdapter
from api.providers.openrouter_adapter import OpenRouterAdapter
from api.router import Router
from api.orchestrator import Orchestrator
from api.controllers import chat
from api.schemas import HealthResponse
from api import metrics

# Configurar logging
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager para startup y shutdown.
    """
    # ========== STARTUP ==========
    logger.info(f"Iniciando {settings.app_name} v{settings.app_version}")
    logger.info(f"Entorno: {settings.app_env}")

    # Crear clientes de infraestructura
    http_client = create_http_client(timeout=settings.provider_timeout)
    await http_client.__aenter__()

    redis_client = await create_redis_client(settings.redis_url)

    # Crear adapters de proveedores
    providers: list[ProviderAdapter] = []

    if settings.groq_api_key:
        groq_adapter = GroqAdapter(
            http_client=http_client,
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            timeout=settings.provider_timeout,
        )
        providers.append(groq_adapter)
        logger.info("Proveedor Groq configurado")
    else:
        logger.warning("GROQ_API_KEY no configurada, Groq no estará disponible")

    if settings.openrouter_api_key:
        openrouter_adapter = OpenRouterAdapter(
            http_client=http_client,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=settings.provider_timeout,
        )
        providers.append(openrouter_adapter)
        logger.info("Proveedor OpenRouter configurado")
    else:
        logger.warning(
            "OPENROUTER_API_KEY no configurada, " "OpenRouter no estará disponible"
        )

    if not providers:
        logger.error(
            "No hay proveedores configurados. "
            "La aplicación no funcionará correctamente."
        )

    # Crear router y orchestrator
    providers_seq: Sequence[ProviderAdapter] = providers
    router_instance = Router(
        providers=providers_seq,
        redis_client=redis_client,
        settings=settings,
        first_chunk_timeout=settings.first_chunk_timeout,
        backoff_base=settings.backoff_base_seconds,
        backoff_max=settings.backoff_max_seconds,
    )

    orchestrator = Orchestrator(
        router=router_instance, max_operation_timeout=settings.max_operation_timeout
    )

    # Guardar en app state
    app.state.http_client = http_client
    app.state.redis_client = redis_client
    app.state.router = router_instance
    app.state.orchestrator = orchestrator
    app.state.providers = providers

    logger.info(f"Aplicación iniciada correctamente en {settings.host}:{settings.port}")

    yield

    # ========== SHUTDOWN ==========
    logger.info("Cerrando aplicación...")

    await http_client.__aexit__(None, None, None)
    await redis_client.disconnect()

    logger.info("Aplicación cerrada correctamente")


# Crear app FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API de orquestación de proveedores LLM con streaming",
    lifespan=lifespan,
)


# ========== Middleware ==========

# CORS (ajustar según necesidades)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_tracking(request: Request, call_next: Any) -> Response:
    """
    Middleware para tracking de requests y métricas.
    """
    start_time = time.time()

    # Procesar request
    response = cast(Response, await call_next(request))

    # Calcular duración
    duration = time.time() - start_time

    # Registrar métricas
    route = request.url.path
    method = request.method
    status = response.status_code

    metrics.record_request(route, method, status)
    metrics.record_latency(route, duration)

    # Añadir headers de respuesta
    response.headers["X-Process-Time"] = str(duration)

    return response


# ========== Routes ==========


# Health check
@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """
    Endpoint de health check.

    Verifica estado de la aplicación y proveedores.
    """
    providers_status = {}

    for provider in request.app.state.providers:
        # Verificar si está blacklisted
        is_blacklisted = await request.app.state.redis_client.is_provider_blacklisted(
            provider.name
        )

        if is_blacklisted:
            providers_status[provider.name] = "blacklisted"
        else:
            providers_status[provider.name] = "available"

    return HealthResponse(
        status="healthy", version=settings.app_version, providers=providers_status
    )


# Métricas Prometheus
@app.get("/metrics")
async def get_metrics() -> Response:
    """
    Endpoint de métricas Prometheus.
    """
    return metrics.get_metrics()


# Incluir routers de controllers
app.include_router(chat.router, tags=["chat"])


# ========== Handlers de errores globales ==========


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler global para excepciones no capturadas.
    """
    logger.error(f"Error no manejado: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Error interno del servidor",
            "detail": str(exc) if settings.app_env == "development" else None,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
