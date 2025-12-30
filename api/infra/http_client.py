"""
Cliente HTTP asíncrono basado en httpx.
Encapsula configuración de timeouts, headers y manejo de errores HTTP.
"""
import httpx
from collections.abc import AsyncIterator
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class HTTPClient:
    """Cliente HTTP asíncrono con configuración centralizada."""
    
    def __init__(
        self,
        timeout: float = 30.0,
        follow_redirects: bool = True,
        max_redirects: int = 5
    ):
        """
        Inicializa el cliente HTTP.
        
        Args:
            timeout: Timeout por defecto en segundos
            follow_redirects: Si seguir redirecciones automáticamente
            max_redirects: Número máximo de redirecciones
        """
        self.timeout = httpx.Timeout(timeout)
        self.client: Optional[httpx.AsyncClient] = None
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
    
    async def __aenter__(self) -> 'HTTPClient':
        """Context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=self.follow_redirects,
            max_redirects=self.max_redirects
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def _get_client(self) -> httpx.AsyncClient:
        """Obtiene el cliente, validando que esté inicializado."""
        if not self.client:
            raise RuntimeError("HTTPClient no inicializado. Usa como context manager.")
        return self.client
    
    async def post(
        self,
        url: str,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """
        Realiza un POST request.
        
        Args:
            url: URL destino
            json: Payload JSON
            headers: Headers HTTP adicionales
            timeout: Timeout específico para esta request
            
        Returns:
            Respuesta HTTP
        """
        client = self._get_client()
        timeout_config = httpx.Timeout(timeout) if timeout else self.timeout
        
        response = await client.post(
            url,
            json=json,
            headers=headers,
            timeout=timeout_config
        )
        
        return response
    
    async def stream_post(
        self,
        url: str,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[float] = None
    ) -> AsyncIterator[bytes]:
        """
        Realiza un POST request con streaming de la respuesta.
        
        Args:
            url: URL destino
            json: Payload JSON
            headers: Headers HTTP adicionales
            timeout: Timeout específico para esta request
            
        Yields:
            Chunks de bytes de la respuesta
        """
        client = self._get_client()
        timeout_config = httpx.Timeout(timeout) if timeout else self.timeout
        
        async with client.stream(
            'POST',
            url,
            json=json,
            headers=headers,
            timeout=timeout_config
        ) as response:
            # Verificar status code antes de empezar a streamear
            response.raise_for_status()
            
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk


def create_http_client(timeout: float = 30.0) -> HTTPClient:
    """
    Factory function para crear un HTTPClient.
    
    Args:
        timeout: Timeout por defecto
        
    Returns:
        Instancia de HTTPClient
    """
    return HTTPClient(timeout=timeout)
