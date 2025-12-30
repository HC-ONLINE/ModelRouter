"""
Adapter para OpenRouter API.
Implementa el contrato ProviderAdapter para interactuar con OpenRouter.
"""

from collections.abc import AsyncGenerator
import json
import logging
import httpx

from api.providers.base import ProviderAdapter
from api.schemas import ChatRequest, ChatResponse, ProviderError

logger = logging.getLogger(__name__)


class OpenRouterAdapter(ProviderAdapter):
    """Adapter para OpenRouter API compatible con OpenAI."""

    name = "openrouter"

    # Modelo por defecto en OpenRouter
    DEFAULT_MODEL = "openai/gpt-3.5-turbo"

    def _build_payload(self, request: ChatRequest) -> dict:
        """
        Construye el payload para OpenRouter API.

        Args:
            request: Request interna normalizada

        Returns:
            Payload en formato OpenRouter/OpenAI
        """
        messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        payload = {
            "model": request.model or self.DEFAULT_MODEL,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": request.stream,
        }

        return payload

    def _get_headers(self) -> dict[str, str]:
        """
        Headers específicos para OpenRouter.
        OpenRouter requiere headers adicionales para identificación.
        """
        headers = super()._get_headers()
        headers.update(
            {
                # Requerido por OpenRouter
                "HTTP-Referer": "https://github.com/modelrouter",
                # Opcional pero recomendado
                "X-Title": "ModelRouter",
            }
        )
        return headers

    async def stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Streaming de respuesta desde OpenRouter.

        OpenRouter usa Server-Sent Events (SSE) con formato OpenAI:
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
                                f"[OpenRouter] No se pudo parsear chunk: {data_str}"
                            )
                            continue

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))

        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con OpenRouter: {str(e)}",
                retriable=True,
                original_error=e,
            )

        except Exception as e:
            logger.error(f"[OpenRouter] Error inesperado en streaming: {str(e)}")
            raise ProviderError(
                provider=self.name,
                code="UNKNOWN_ERROR",
                message=f"Error inesperado: {str(e)}",
                retriable=False,
                original_error=e,
            )

    async def generate(self, request: ChatRequest) -> ChatResponse:
        """
        Generación completa (no streaming) desde OpenRouter.
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
                    "native_tokens_prompt": usage.get("native_tokens_prompt"),
                    "native_tokens_completion": usage.get("native_tokens_completion"),
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
                    message="Respuesta de OpenRouter no contiene choices",
                    retriable=False,
                )

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))

        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con OpenRouter: {str(e)}",
                retriable=True,
                original_error=e,
            )

        except Exception as e:
            logger.error(f"[OpenRouter] Error inesperado: {str(e)}")
            raise ProviderError(
                provider=self.name,
                code="UNKNOWN_ERROR",
                message=f"Error inesperado: {str(e)}",
                retriable=False,
                original_error=e,
            )
