"""
Cliente Redis para manejo de estado, blacklist, rate limiting.
"""
import redis.asyncio as aioredis
from redis.asyncio import Redis
from typing import Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RedisClient:
    """Cliente Redis asíncrono con operaciones de alto nivel."""
    
    def __init__(self, redis_url: str):
        """
        Inicializa el cliente Redis.
        
        Args:
            redis_url: URL de conexión Redis (ej: redis://localhost:6379/0)
        """
        self.redis_url = redis_url
        self.client: Optional[Redis] = None
    
    async def connect(self) -> None:
        """Establece conexión con Redis."""
        self.client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Conexión a Redis establecida")
    
    async def disconnect(self) -> None:
        """Cierra la conexión con Redis."""
        if self.client:
            await self.client.close()
            logger.info("Conexión a Redis cerrada")
    
    def _get_client(self) -> Redis:
        """Valida y obtiene el cliente Redis."""
        if not self.client:
            raise RuntimeError("RedisClient no conectado. Llama a connect() primero.")
        return self.client
    
    # ========== Blacklist de proveedores ==========
    
    async def is_provider_blacklisted(self, provider: str) -> bool:
        """
        Verifica si un proveedor está en blacklist temporal.
        
        Args:
            provider: Nombre del proveedor
            
        Returns:
            True si está blacklisted, False en caso contrario
        """
        client = self._get_client()
        key = f"blacklist:{provider}"
        value = await client.get(key)
        return value is not None
    
    async def blacklist_provider(
        self,
        provider: str,
        seconds: int
    ) -> None:
        """
        Añade un proveedor a la blacklist temporal.
        
        Args:
            provider: Nombre del proveedor
            seconds: Duración de la blacklist en segundos
        """
        client = self._get_client()
        key = f"blacklist:{provider}"
        await client.setex(key, seconds, "1")
        logger.warning(f"Proveedor {provider} añadido a blacklist por {seconds}s")
    
    # ========== Contadores de fallos ==========
    
    async def increment_failure_count(self, provider: str) -> int:
        """
        Incrementa el contador de fallos de un proveedor.
        
        Args:
            provider: Nombre del proveedor
            
        Returns:
            Nuevo valor del contador
        """
        client = self._get_client()
        key = f"failures:{provider}"
        count = await client.incr(key)
        await client.expire(key, 300)  # Expira en 5 minutos
        return count
    
    async def reset_failure_count(self, provider: str) -> None:
        """
        Resetea el contador de fallos de un proveedor.
        
        Args:
            provider: Nombre del proveedor
        """
        client = self._get_client()
        key = f"failures:{provider}"
        await client.delete(key)
    
    async def get_failure_count(self, provider: str) -> int:
        """
        Obtiene el contador de fallos de un proveedor.
        
        Args:
            provider: Nombre del proveedor
            
        Returns:
            Número de fallos actuales
        """
        client = self._get_client()
        key = f"failures:{provider}"
        value = await client.get(key)
        return int(value) if value else 0
    
    # ========== Rate limiting ==========
    
    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Verifica y actualiza rate limit para un identificador.
        
        Args:
            identifier: Identificador único (API key, IP, etc.)
            max_requests: Máximo de requests permitidas
            window_seconds: Ventana de tiempo en segundos
            
        Returns:
            Tupla (permitido, requests_restantes)
        """
        client = self._get_client()
        key = f"ratelimit:{identifier}"
        
        current = await client.get(key)
        
        if current is None:
            # Primera request en la ventana
            await client.setex(key, window_seconds, "1")
            return True, max_requests - 1
        
        count = int(current)
        
        if count >= max_requests:
            return False, 0
        
        await client.incr(key)
        return True, max_requests - count - 1
    
    # ========== Concurrencia ==========
    
    async def acquire_slot(self, resource: str, max_slots: int, ttl: int = 300) -> bool:
        """
        Intenta adquirir un slot de concurrencia.
        
        Args:
            resource: Identificador del recurso
            max_slots: Máximo de slots concurrentes
            ttl: Time-to-live del slot en segundos
            
        Returns:
            True si se adquirió el slot, False si no hay disponibles
        """
        client = self._get_client()
        key = f"concurrency:{resource}"
        
        current = await client.get(key)
        current_count = int(current) if current else 0
        
        if current_count >= max_slots:
            return False
        
        await client.incr(key)
        await client.expire(key, ttl)
        return True
    
    async def release_slot(self, resource: str) -> None:
        """
        Libera un slot de concurrencia.
        
        Args:
            resource: Identificador del recurso
        """
        client = self._get_client()
        key = f"concurrency:{resource}"
        
        current = await client.get(key)
        if current and int(current) > 0:
            await client.decr(key)


async def create_redis_client(redis_url: str) -> RedisClient:
    """
    Factory function para crear y conectar un RedisClient.
    
    Args:
        redis_url: URL de conexión Redis
        
    Returns:
        RedisClient conectado
    """
    client = RedisClient(redis_url)
    await client.connect()
    return client
