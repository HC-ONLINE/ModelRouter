"""
Adapter para Ollama API (modelos locales).
Implementa el contrato ProviderAdapter para interactuar con Ollama.
"""

from collections.abc import AsyncGenerator
import json
import logging
from typing import Optional
import httpx

from api.providers.base import ProviderAdapter
from api.schemas import ChatRequest, ChatResponse, ProviderError
from api.infra.http_client import HTTPClient

logger = logging.getLogger(__name__)


class OllamaAdapter(ProviderAdapter):
    """Adapter para Ollama API compatible con OpenAI."""

    name = "ollama"

    # Modelo por defecto en Ollama
    DEFAULT_MODEL = "llama3.2:1b"

    def __init__(
        self,
        http_client: HTTPClient,
        api_key: str = "",  # Ollama no requiere API key por defecto
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0,
        default_model: Optional[str] = None,
    ):
        """
        Inicializa el adapter de Ollama.

        Args:
            http_client: Cliente HTTP asíncrono
            api_key: API key (opcional, Ollama local no lo requiere)
            base_url: URL base de Ollama (por defecto localhost:11434)
            timeout: Timeout por defecto para requests
            default_model: Modelo por defecto cuando no se especifica en la request
        """
        super().__init__(http_client, api_key, base_url, timeout)
        self.default_model = default_model or self.DEFAULT_MODEL

    def _get_headers(self) -> dict[str, str]:
        """
        Construye headers para requests a Ollama.
        Ollama local no requiere autenticación por defecto.

        Returns:
            Diccionario de headers HTTP
        """
        headers = {"Content-Type": "application/json"}

        # Solo agregar Authorization si hay API key configurada
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def _messages_to_prompt(self, request: ChatRequest) -> str:
        """
        Convierte los mensajes en un prompt simple para Ollama.

        Args:
            request: Request interna normalizada

        Returns:
            String con el prompt formateado
        """
        # Convertir mensajes a prompt simple
        # Formato: [System] system_msg\n[User] user_msg\n[Assistant] assistant_msg
        prompt_parts = []

        for msg in request.messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")

        return "\n".join(prompt_parts)

    def _build_payload(self, request: ChatRequest) -> dict:
        """
        Construye el payload para Ollama API.

        Args:
            request: Request interna normalizada

        Returns:
            Payload en formato compatible con Ollama (/api/generate)
        """
        # Ollama /api/generate usa "prompt" (string), no "messages" (array)
        prompt = self._messages_to_prompt(request)

        payload = {
            "model": request.model or self.default_model,
            "prompt": prompt,
            "stream": request.stream,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        return payload

    async def stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Streaming de respuesta desde Ollama.

        Ollama /api/generate usa streaming JSON line-delimited con formato:
        {"response": "texto", "done": false}
        """
        request.stream = True
        payload = self._build_payload(request)
        url = f"{self.base_url}/api/generate"
        headers = self._get_headers()

        try:
            async for chunk_bytes in self.http_client.stream_post(
                url=url, json=payload, headers=headers, timeout=self.timeout
            ):
                # Decodificar chunk
                chunk_text = chunk_bytes.decode("utf-8")

                # Ollama envía líneas JSON completas
                for line in chunk_text.strip().split("\n"):
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # Extraer contenido de la respuesta
                        if "response" in data:
                            content = data.get("response", "")
                            if content:
                                yield content

                        # Verificar si es el último chunk
                        if data.get("done", False):
                            break

                    except json.JSONDecodeError:
                        logger.warning(f"[Ollama] No se pudo parsear chunk: {line}")
                        continue

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))

        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con Ollama: {str(e)}",
                retriable=True,
                original_error=e,
            )

        except Exception as e:
            from api.utils import log_provider_error

            log_provider_error(
                logger,
                provider=self.name,
                error_code="UNKNOWN_ERROR",
                request_id=getattr(request, "request_id", None),
                exc=e,
            )
            raise ProviderError(
                provider=self.name,
                code="UNKNOWN_ERROR",
                message=f"Error inesperado: {str(e)}",
                retriable=False,
                original_error=e,
            )

    async def generate(self, request: ChatRequest) -> ChatResponse:
        """
        Generación completa (no streaming) desde Ollama.
        """
        request.stream = False
        payload = self._build_payload(request)
        url = f"{self.base_url}/api/generate"
        headers = self._get_headers()

        try:
            response = await self.http_client.post(
                url=url, json=payload, headers=headers, timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            # Extraer texto de la respuesta
            if "response" in data:
                text = data.get("response", "")
                model_used = data.get("model", self.DEFAULT_MODEL)

                # Extraer metadata útil
                provider_meta = {
                    "model": model_used,
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                    "done": data.get("done", False),
                }

                return ChatResponse(
                    text=text,
                    provider=self.name,
                    model=model_used,
                    provider_meta=provider_meta,
                )

            else:
                raise ProviderError(
                    provider=self.name,
                    code="INVALID_RESPONSE",
                    message="Respuesta de Ollama no contiene 'response'",
                    retriable=False,
                )

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))

        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con Ollama: {str(e)}",
                retriable=True,
                original_error=e,
            )

        except Exception as e:
            from api.utils import log_provider_error

            log_provider_error(
                logger,
                provider=self.name,
                error_code="UNKNOWN_ERROR",
                request_id=getattr(request, "request_id", None),
                exc=e,
            )
            raise ProviderError(
                provider=self.name,
                code="UNKNOWN_ERROR",
                message=f"Error inesperado: {str(e)}",
                retriable=False,
                original_error=e,
            )
