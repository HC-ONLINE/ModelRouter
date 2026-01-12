"""
Adapter para Groq API.
Implementa el contrato ProviderAdapter para interactuar con Groq.
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


class GroqAdapter(ProviderAdapter):
    """Adapter para Groq API compatible con OpenAI."""

    name = "groq"

    # Modelos disponibles en Groq
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(
        self,
        http_client: HTTPClient,
        api_key: str,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 30.0,
        default_model: Optional[str] = None,
    ):
        """
        Inicializa el adapter de Groq.

        Args:
            http_client: Cliente HTTP asíncrono
            api_key: API key de Groq
            base_url: URL base de Groq API
            timeout: Timeout por defecto para requests
            default_model: Modelo por defecto cuando no se especifica en la request
        """
        super().__init__(http_client, api_key, base_url, timeout)
        self.default_model = default_model or self.DEFAULT_MODEL

    def _build_payload(self, request: ChatRequest) -> dict:
        """
        Construye el payload para Groq API.

        Args:
            request: Request interna normalizada

        Returns:
            Payload en formato Groq/OpenAI
        """
        messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        payload = {
            "model": request.model or self.default_model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": request.stream,
        }

        return payload

    async def stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Streaming de respuesta desde Groq.

        La API de Groq usa Server-Sent Events (SSE) con formato:
        data: {"choices": [{"delta": {"content": "texto"}}]}
        """
        request.stream = True
        payload = self._build_payload(request)
        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()

        try:
            async for chunk_bytes in self.http_client.stream_post(
                url=url, json=payload, headers=headers, timeout=self.timeout
            ):
                # Decodificar chunk
                chunk_text = chunk_bytes.decode("utf-8")

                # Parsear líneas SSE
                for line in chunk_text.split("\n"):
                    line = line.strip()

                    if not line or line.startswith(":"):
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]  # Remover 'data: '

                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)

                            # Extraer contenido del delta
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")

                                if content:
                                    yield content

                        except json.JSONDecodeError:
                            logger.warning(
                                f"[Groq] No se pudo parsear chunk: {data_str}"
                            )
                            continue

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))

        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con Groq: {str(e)}",
                retriable=True,
                original_error=e,
            )

        except Exception as e:
            logger.error(f"[Groq] Error inesperado en streaming: {str(e)}")
            raise ProviderError(
                provider=self.name,
                code="UNKNOWN_ERROR",
                message=f"Error inesperado: {str(e)}",
                retriable=False,
                original_error=e,
            )

    async def generate(self, request: ChatRequest) -> ChatResponse:
        """
        Generación completa (no streaming) desde Groq.
        """
        request.stream = False
        payload = self._build_payload(request)
        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()

        try:
            response = await self.http_client.post(
                url=url, json=payload, headers=headers, timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            # Extraer texto de la respuesta
            if "choices" in data and len(data["choices"]) > 0:
                text = data["choices"][0]["message"]["content"]
                model_used = data.get("model", self.DEFAULT_MODEL)

                # Extraer metadata útil
                usage = data.get("usage", {})
                provider_meta = {
                    "model": model_used,
                    "tokens_prompt": usage.get("prompt_tokens", 0),
                    "tokens_completion": usage.get("completion_tokens", 0),
                    "tokens_total": usage.get("total_tokens", 0),
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
                    message="Respuesta de Groq no contiene choices",
                    retriable=False,
                )

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))

        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con Groq: {str(e)}",
                retriable=True,
                original_error=e,
            )

        except Exception as e:
            logger.error(f"[Groq] Error inesperado: {str(e)}")
            raise ProviderError(
                provider=self.name,
                code="UNKNOWN_ERROR",
                message=f"Error inesperado: {str(e)}",
                retriable=False,
                original_error=e,
            )
