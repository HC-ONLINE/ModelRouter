"""
Router: lógica de selección de proveedor y fallback.
Mantiene estado de proveedores y coordina rotación ante fallos.
"""

from collections.abc import AsyncIterator, Sequence
from typing import Optional
import asyncio
import logging

from api.providers.base import ProviderAdapter
from api.schemas import ChatRequest, ChatResponse, ProviderError
from api.infra.redis_client import RedisClient
from api.config import Settings

logger = logging.getLogger(__name__)


class Router:
    """
    Router que selecciona y gestiona fallback entre proveedores.

    Responsabilidades:
    - Mantener lista ordenada de proveedores
    - Verificar blacklist antes de intentar cada proveedor
    - Verificar rate limits por proveedor
    - Coordinar fallback si un proveedor falla
    - Actualizar estado en Redis (blacklist, contadores)
    """

    def __init__(
        self,
        providers: Sequence[ProviderAdapter],
        redis_client: RedisClient,
        settings: Settings,
        first_chunk_timeout: float = 3.0,
        backoff_base: int = 5,
        backoff_max: int = 300,
    ):
        """
        Inicializa el router.

        Args:
            providers: Lista ordenada de proveedores (el primero tiene más prioridad)
            redis_client: Cliente Redis para gestión de estado
            settings: Configuración de la aplicación
            first_chunk_timeout: Timeout para esperar el primer chunk en streaming
            backoff_base: Segundos base para backoff exponencial
            backoff_max: Máximo de segundos para backoff
        """
        self.providers = list(providers)
        self.redis = redis_client
        self.settings = settings
        self.first_chunk_timeout = first_chunk_timeout
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max

    async def _wait_for_first_chunk(
        self, stream: AsyncIterator[str], timeout: float
    ) -> tuple[Optional[str], AsyncIterator[str]]:
        """
        Espera el primer chunk con timeout.

        Args:
            stream: Stream async iterator
            timeout: Timeout en segundos

        Returns:
            Tupla (primer_chunk, stream_restante)
            Si no llega chunk en timeout, retorna (None, stream)
        """
        try:
            first_chunk = await asyncio.wait_for(stream.__anext__(), timeout=timeout)

            # Crear un nuevo iterador que incluya el primer chunk
            async def full_stream() -> AsyncIterator[str]:
                yield first_chunk
                async for chunk in stream:
                    yield chunk

            return first_chunk, full_stream()

        except asyncio.TimeoutError:
            logger.warning(f"Timeout esperando primer chunk ({timeout}s)")
            return None, stream

        except StopAsyncIteration:
            # Stream vacío
            return None, stream

    async def _mark_provider_failed(self, provider: ProviderAdapter) -> None:
        """
        Marca un proveedor como fallido y aplica backoff.

        Args:
            provider: Proveedor que falló
        """
        # Incrementar contador de fallos
        failure_count = await self.redis.increment_failure_count(provider.name)

        # Calcular backoff exponencial
        backoff_seconds = min(
            self.backoff_base * (2 ** (failure_count - 1)), self.backoff_max
        )

        # Añadir a blacklist temporal
        await self.redis.blacklist_provider(provider.name, backoff_seconds)

        logger.warning(
            f"Proveedor {provider.name} marcado como fallido. "
            f"Fallos consecutivos: {failure_count}. "
            f"Blacklist por {backoff_seconds}s"
        )

    async def _mark_provider_success(self, provider: ProviderAdapter) -> None:
        """
        Marca un proveedor como exitoso y resetea contadores.

        Args:
            provider: Proveedor que tuvo éxito
        """
        await self.redis.reset_failure_count(provider.name)

    async def choose_and_stream(
        self, request: ChatRequest, request_id: str
    ) -> AsyncIterator[str]:
        """
        Selecciona proveedor y genera stream con fallback automático.

        Algoritmo:
        1. Itera proveedores en orden de prioridad
        2. Salta proveedores blacklisted
        3. Intenta streamear
        4. Espera primer chunk con timeout
        5. Si no llega, prueba siguiente proveedor
        6. Si llega, commit a ese proveedor y streamea todo

        Args:
            request: ChatRequest normalizado
            request_id: ID de la request para logging

        Yields:
            Chunks de texto generados

        Raises:
            ProviderError: Si todos los proveedores fallan
        """
        last_error: Optional[ProviderError] = None

        for provider in self.providers:
            # Verificar blacklist
            if await self.redis.is_provider_blacklisted(provider.name):
                logger.info(
                    f"[{request_id}] Proveedor {provider.name} en blacklist, saltando"
                )
                continue

            # Verificar rate limit específico del proveedor
            rate_limit_error = await self._check_provider_rate_limit(
                provider, request_id
            )
            if rate_limit_error:
                last_error = rate_limit_error
                continue

            try:
                # Iniciar streaming
                stream = provider.stream(request)

                # Esperar primer chunk
                first_chunk, full_stream = await self._wait_for_first_chunk(
                    stream, self.first_chunk_timeout
                )

                if first_chunk is None:
                    # No llegó primer chunk a tiempo
                    logger.warning(
                        f"[{request_id}] {provider.name} no emitió primer chunk "
                        f"en {self.first_chunk_timeout}s"
                    )
                    await self._mark_provider_failed(provider)
                    continue

                # Éxito: tenemos el primer chunk
                logger.info(
                    f"[{request_id}] {provider.name} emitió primer chunk, "
                    "commiteando a este proveedor"
                )

                # Streamear todo el contenido
                async for chunk in full_stream:
                    yield chunk

                # Marcar como exitoso al finalizar
                await self._mark_provider_success(provider)
                return

            except ProviderError as e:
                logger.error(
                    f"[{request_id}] Error en {provider.name}: {e.code} - {e.message}"
                )
                last_error = e

                # Si es retriable, marcar como fallido para backoff
                if e.retriable:
                    await self._mark_provider_failed(provider)

                # Continuar con siguiente proveedor
                continue

            except Exception as e:
                logger.error(
                    f"[{request_id}] Error inesperado en {provider.name}: {str(e)}"
                )
                last_error = ProviderError(
                    provider=provider.name,
                    code="UNKNOWN_ERROR",
                    message=str(e),
                    retriable=False,
                )
                continue

        # Si llegamos aquí, todos los proveedores fallaron
        error_msg = "Todos los proveedores fallaron"
        if last_error:
            error_msg += f". Último error: {last_error.message}"

        raise ProviderError(
            provider="router",
            code="ALL_PROVIDERS_FAILED",
            message=error_msg,
            retriable=False,
        )

    async def choose_and_generate(
        self, request: ChatRequest, request_id: str
    ) -> ChatResponse:
        """
        Selecciona proveedor y genera respuesta completa con fallback.

        Args:
            request: ChatRequest normalizado
            request_id: ID de la request para logging

        Returns:
            ChatResponse generado

        Raises:
            ProviderError: Si todos los proveedores fallan
        """
        last_error: Optional[ProviderError] = None

        for provider in self.providers:
            # Verificar blacklist
            if await self.redis.is_provider_blacklisted(provider.name):
                logger.info(
                    f"[{request_id}] Proveedor {provider.name} en blacklist, saltando"
                )
                continue

            # Verificar rate limit específico del proveedor
            rate_limit_error = await self._check_provider_rate_limit(
                provider, request_id
            )
            if rate_limit_error:
                last_error = rate_limit_error
                continue

            try:
                response = await provider.generate(request)

                # Éxito
                logger.info(
                    f"[{request_id}] {provider.name} generó respuesta exitosamente"
                )
                await self._mark_provider_success(provider)
                return response

            except ProviderError as e:
                logger.error(
                    f"[{request_id}] Error en {provider.name}: {e.code} - {e.message}"
                )
                last_error = e

                if e.retriable:
                    await self._mark_provider_failed(provider)

                continue

            except Exception as e:
                logger.error(
                    f"[{request_id}] Error inesperado en {provider.name}: {str(e)}"
                )
                last_error = ProviderError(
                    provider=provider.name,
                    code="UNKNOWN_ERROR",
                    message=str(e),
                    retriable=False,
                )
                continue

        # Todos los proveedores fallaron
        error_msg = "Todos los proveedores fallaron"
        if last_error:
            error_msg += f". Último error: {last_error.message}"

        raise ProviderError(
            provider="router",
            code="ALL_PROVIDERS_FAILED",
            message=error_msg,
            retriable=False,
        )

    async def _check_provider_rate_limit(
        self, provider: ProviderAdapter, request_id: str
    ) -> Optional[ProviderError]:
        provider_rate_limit = self.settings.get_provider_rate_limit(provider.name)

        allowed, remaining = await self.redis.check_provider_rate_limit(
            provider_name=provider.name,
            user_id=request_id,
            max_requests=provider_rate_limit,
            window_seconds=60,
        )

        if not allowed:
            logger.warning(
                f"[{request_id}] Rate limit excedido para {provider.name}, saltando"
            )
            return ProviderError(
                provider=provider.name,
                code="RATE_LIMIT",
                message=f"Rate limit de {provider_rate_limit} req/min excedido",
                retriable=True,
            )

        logger.info(
            f"[{request_id}] Intentando con proveedor: {provider.name} "
            f"(rate limit: {remaining}/{provider_rate_limit} restantes)"
        )

        return None
