"""
Controller para endpoints de chat.
Maneja validación de entrada, autorización y respuestas HTTP.
"""

from fastapi import APIRouter, HTTPException, Header, Request as FastAPIRequest
from fastapi.responses import StreamingResponse
from collections.abc import AsyncIterator
from typing import Optional
import logging

from api.schemas import ChatRequest, ChatResponse, ProviderError
from api.orchestrator import Orchestrator
from api.utils import generate_request_id, RequestLogger
from api.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_api_key(authorization: Optional[str] = Header(None)) -> None:
    """
    Verifica la API key del cliente.

    Args:
        authorization: Header Authorization con formato "Bearer <key>"

    Raises:
        HTTPException: Si la API key es inválida o falta
    """
    # Si no hay API key configurada, no validar (modo desarrollo)
    if not settings.api_key:
        return

    if not authorization:
        raise HTTPException(status_code=401, detail="Falta header Authorization")

    # Extraer token del header
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Formato de Authorization inválido. Usar: Bearer <token>",
        )

    token = parts[1]
    if token != settings.api_key:
        raise HTTPException(status_code=401, detail="API key inválida")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    fastapi_request: FastAPIRequest,
    authorization: Optional[str] = Header(None),
) -> ChatResponse:
    """
    Endpoint para generación completa (no streaming).

    Args:
        request: ChatRequest con mensajes y parámetros
        fastapi_request: Request de FastAPI para acceso a state
        authorization: Header de autorización

    Returns:
        ChatResponse con texto generado y metadatos

    Raises:
        HTTPException: En caso de error (401, 503, etc.)
    """
    # Verificar autorización
    verify_api_key(authorization)

    # Generar request ID
    request_id = generate_request_id()
    req_logger = RequestLogger(request_id, logger)

    # Obtener orchestrator desde app state
    orchestrator: Orchestrator = fastapi_request.app.state.orchestrator

    req_logger.info(
        "Request /chat recibida",
        num_messages=len(request.messages),
        max_tokens=request.max_tokens,
    )

    try:
        # Generar respuesta
        response = await orchestrator.generate_response(request, request_id)

        req_logger.info(
            "Request /chat completada",
            provider=response.provider,
            text_length=len(response.text),
        )

        return response

    except ProviderError as e:
        from api.utils import log_provider_error

        log_provider_error(
            logger,
            provider=e.provider,
            error_code=e.code,
            request_id=request_id,
            exc=e,
        )
        # Mapear a status code HTTP apropiado
        if e.code == "RATE_LIMIT":
            status_code = 429
        elif e.code in ["UNAUTHORIZED", "FORBIDDEN"]:
            status_code = 403
        elif e.code == "INVALID_PROVIDER":
            status_code = 400
        elif e.code == "ALL_PROVIDERS_FAILED":
            status_code = 503
        else:
            status_code = 500
        raise HTTPException(
            status_code=status_code,
            detail={"error": e.code, "message": e.message, "request_id": request_id},
        )
    except Exception as e:
        from api.utils import log_provider_error

        log_provider_error(
            logger,
            provider="controller",
            error_code="INTERNAL_ERROR",
            request_id=request_id,
            exc=e,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": str(e),
                "request_id": request_id,
            },
        )


@router.post("/stream")
async def stream(
    request: ChatRequest,
    fastapi_request: FastAPIRequest,
    authorization: Optional[str] = Header(None),
) -> StreamingResponse:
    """
    Endpoint para generación con streaming (SSE).

    Args:
        request: ChatRequest con mensajes y parámetros
        fastapi_request: Request de FastAPI para acceso a state
        authorization: Header de autorización

    Returns:
        StreamingResponse con Server-Sent Events

    Raises:
        HTTPException: En caso de error (401, 503, etc.)
    """
    # Verificar autorización
    verify_api_key(authorization)

    # Generar request ID
    request_id = generate_request_id()
    req_logger = RequestLogger(request_id, logger)

    # Obtener orchestrator desde app state
    orchestrator: Orchestrator = fastapi_request.app.state.orchestrator

    req_logger.info(
        "Request /stream recibida",
        num_messages=len(request.messages),
        max_tokens=request.max_tokens,
    )

    # Forzar stream en el request
    request.stream = True

    async def sse_generator() -> AsyncIterator[str]:
        """
        Genera Server-Sent Events desde el stream del orchestrator.
        """
        try:
            async for chunk in orchestrator.stream_response(request, request_id):
                # Formato SSE: data: <contenido>\n\n
                yield f"data: {chunk}\n\n"

            # Señal de finalización
            yield "data: [DONE]\n\n"

            req_logger.info("Request /stream completada")

        except ProviderError as e:
            from api.utils import log_provider_error

            log_provider_error(
                logger,
                provider=e.provider,
                error_code=e.code,
                request_id=request_id,
                exc=e,
            )
            # Enviar error como SSE
            error_data = {
                "error": e.code,
                "message": e.message,
                "request_id": request_id,
            }
            yield f"data: {error_data}\n\n"
        except Exception as e:
            from api.utils import log_provider_error

            log_provider_error(
                logger,
                provider="controller",
                error_code="INTERNAL_ERROR",
                request_id=request_id,
                exc=e,
            )
            error_data = {
                "error": "INTERNAL_ERROR",
                "message": str(e),
                "request_id": request_id,
            }
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )
