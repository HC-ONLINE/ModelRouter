"""
Interfaz base abstracta para adapters de proveedores LLM.
Define el contrato que todos los proveedores deben cumplir.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
import logging

from api.schemas import ChatRequest, ChatResponse, ProviderError
from api.infra.http_client import HTTPClient

logger = logging.getLogger(__name__)


class ProviderAdapter(ABC):
    """
    Clase base abstracta para adapters de proveedores.

    Cada proveedor debe implementar los métodos stream() y generate()
    traduciendo el ChatRequest interno al formato específico del proveedor.
    """

    # Nombre del proveedor (debe ser definido por cada implementación)
    name: str = "base"

    def __init__(
        self,
        http_client: HTTPClient,
        api_key: str,
        base_url: str,
        timeout: float = 30.0,
    ):
        """
        Inicializa el adapter.

        Args:
            http_client: Cliente HTTP asíncrono
            api_key: API key del proveedor
            base_url: URL base de la API del proveedor
            timeout: Timeout por defecto para requests
        """
        self.http_client = http_client
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    @abstractmethod
    async def stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Genera respuesta en modo streaming.

        Args:
            request: Request normalizado interno

        Yields:
            Fragmentos de texto generados

        Raises:
            ProviderError: Si hay error en la generación
        """
        raise NotImplementedError
        yield  # Para que sea reconocido como generator

    @abstractmethod
    async def generate(self, request: ChatRequest) -> ChatResponse:
        """
        Genera respuesta completa (no streaming).

        Args:
            request: Request normalizado interno

        Returns:
            Respuesta completa normalizada

        Raises:
            ProviderError: Si hay error en la generación
        """
        raise NotImplementedError

    def _get_headers(self) -> dict[str, str]:
        """
        Construye headers comunes para requests al proveedor.

        Returns:
            Diccionario de headers HTTP
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _handle_http_error(self, status_code: int, message: str) -> ProviderError:
        """
        Convierte errores HTTP en ProviderError con información de retriabilidad.

        Args:
            status_code: Código de estado HTTP
            message: Mensaje de error

        Returns:
            ProviderError apropiado
        """
        retriable = False
        code = f"HTTP_{status_code}"

        # Errores retriables
        if status_code == 429:
            code = "RATE_LIMIT"
            retriable = True
        elif status_code >= 500:
            code = "SERVER_ERROR"
            retriable = True
        elif status_code == 408:
            code = "TIMEOUT"
            retriable = True
        # Errores no retriables
        elif status_code == 401:
            code = "UNAUTHORIZED"
        elif status_code == 403:
            code = "FORBIDDEN"
        elif status_code == 400:
            code = "BAD_REQUEST"

        return ProviderError(
            provider=self.name, code=code, message=message, retriable=retriable
        )

    async def _check_health(self) -> bool:
        """
        Verifica la salud del proveedor (opcional, puede ser sobrescrito).

        Returns:
            True si el proveedor está disponible, False en caso contrario
        """
        # Implementación por defecto: siempre disponible
        # Los proveedores pueden sobrescribir esto
        return True
