"""
Orchestrator: coordina el flujo completo de generación.
Maneja timeouts globales, cancelación y transformaciones de alto nivel.
"""

from collections.abc import AsyncIterator
import asyncio
import logging

from api.router import Router
from api.schemas import ChatRequest, ChatResponse, ProviderError

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orchestrator que coordina el flujo de generación de respuestas.

    Responsabilidades:
    - Validar request de alto nivel
    - Aplicar timeout global a operaciones
    - Coordinar streaming hacia el cliente
    - Manejar cancelación de cliente (close stream)
    - Transformar errores en respuestas HTTP apropiadas
    """

    def __init__(self, router: Router, max_operation_timeout: float = 120.0):
        """
        Inicializa el orchestrator.

        Args:
            router: Router para selección de proveedores
            max_operation_timeout: Timeout máximo para toda la operación
        """
        self.router = router
        self.max_operation_timeout = max_operation_timeout

    async def stream_response(
        self, request: ChatRequest, request_id: str
    ) -> AsyncIterator[str]:
        """
        Orquesta streaming de respuesta con timeout global.

        Args:
            request: ChatRequest validado
            request_id: ID de request para tracking

        Yields:
            Chunks de texto generados

        Raises:
            ProviderError: Si hay error en la generación
            asyncio.TimeoutError: Si se excede timeout global
        """
        logger.info(
            f"[{request_id}] Iniciando stream. "
            f"Max tokens: {request.max_tokens}, "
            f"Temperature: {request.temperature}"
        )

        try:
            # Aplicar timeout global: iniciar un task que cancele si se excede
            chunks_count = 0
            start_time = asyncio.get_event_loop().time()

            async for chunk in self.router.choose_and_stream(request, request_id):
                # Verificar timeout en cada chunk
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.max_operation_timeout:
                    error_msg = (
                        f"Operación excedió timeout global de "
                        f"{self.max_operation_timeout}s"
                    )
                    logger.error(f"[{request_id}] {error_msg}")
                    raise ProviderError(
                        provider="orchestrator",
                        code="GLOBAL_TIMEOUT",
                        message=error_msg,
                        retriable=False,
                    )

                chunks_count += 1
                yield chunk

            logger.info(
                f"[{request_id}] Stream completado. " f"Chunks emitidos: {chunks_count}"
            )

        except asyncio.TimeoutError:
            error_msg = (
                f"Operación excedió timeout global de {self.max_operation_timeout}s"
            )
            logger.error(f"[{request_id}] {error_msg}")
            raise ProviderError(
                provider="orchestrator",
                code="GLOBAL_TIMEOUT",
                message=error_msg,
                retriable=False,
            )

        except ProviderError:
            # Propagar errores de proveedor
            raise

        except Exception as e:
            from api.utils import log_provider_error

            log_provider_error(
                logger,
                provider="orchestrator",
                error_code="UNKNOWN_ERROR",
                request_id=request_id,
                exc=e,
            )
            raise ProviderError(
                provider="orchestrator",
                code="UNKNOWN_ERROR",
                message=f"Error inesperado: {str(e)}",
                retriable=False,
                original_error=e,
            )

    async def generate_response(
        self, request: ChatRequest, request_id: str
    ) -> ChatResponse:
        """
        Orquesta generación completa (no streaming) con timeout global.

        Args:
            request: ChatRequest validado
            request_id: ID de request para tracking

        Returns:
            ChatResponse generado

        Raises:
            ProviderError: Si hay error en la generación
            asyncio.TimeoutError: Si se excede timeout global
        """
        logger.info(
            f"[{request_id}] Iniciando generación no-streaming. "
            f"Max tokens: {request.max_tokens}, "
            f"Temperature: {request.temperature}"
        )

        try:
            # Aplicar timeout global
            response = await asyncio.wait_for(
                self.router.choose_and_generate(request, request_id),
                timeout=self.max_operation_timeout,
            )

            logger.info(
                f"[{request_id}] Generación completada. "
                f"Proveedor: {response.provider}, "
                f"Tokens: {response.provider_meta.get('tokens_total', 'N/A')}"
            )

            return response

        except asyncio.TimeoutError:
            error_msg = (
                f"Operación excedió timeout global de {self.max_operation_timeout}s"
            )
            logger.error(f"[{request_id}] {error_msg}")
            raise ProviderError(
                provider="orchestrator",
                code="GLOBAL_TIMEOUT",
                message=error_msg,
                retriable=False,
            )

        except ProviderError:
            # Propagar errores de proveedor
            raise

        except Exception as e:
            logger.error(f"[{request_id}] Error inesperado en orchestrator: {str(e)}")
            raise ProviderError(
                provider="orchestrator",
                code="UNKNOWN_ERROR",
                message=f"Error inesperado: {str(e)}",
                retriable=False,
                original_error=e,
            )
