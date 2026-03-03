"""
Adapter para OpenAI API.
Implementa el contrato ProviderAdapter para interactuar con OpenAI.
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


class OpenAIAdapter(ProviderAdapter):
    """Adapter para OpenAI API."""

    name = "openai"

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        http_client: HTTPClient,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        default_model: Optional[str] = None,
    ):
        super().__init__(http_client, api_key, base_url, timeout)
        self.default_model = default_model or self.DEFAULT_MODEL

    def _build_payload(self, request: ChatRequest) -> dict:
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
        request.stream = True
        payload = self._build_payload(request)
        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()

        try:
            async for chunk_bytes in self.http_client.stream_post(
                url=url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            ):
                chunk_text = chunk_bytes.decode("utf-8")

                for line in chunk_text.split("\n"):
                    line = line.strip()

                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]

                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content")

                        if content:
                            yield content

                    except Exception:
                        continue

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))
        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con OpenAI: {str(e)}",
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
        request.stream = False
        payload = self._build_payload(request)
        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()

        try:
            response = await self.http_client.post(
                url=url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )

            response.raise_for_status()
            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                provider_meta = {
                    "tokens_prompt": usage.get("prompt_tokens"),
                    "tokens_completion": usage.get("completion_tokens"),
                    "tokens_total": usage.get("total_tokens"),
                }

                return ChatResponse(
                    text=text,
                    provider=self.name,
                    model=data.get("model", self.default_model),
                    provider_meta=provider_meta,
                )
            else:
                raise ProviderError(
                    provider=self.name,
                    code="INVALID_RESPONSE",
                    message="Respuesta de OpenAI no contiene choices",
                    retriable=False,
                )

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))
        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con OpenAI: {str(e)}",
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
