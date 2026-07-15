"""
Adapter para Gemini API.
Implementa el contrato ProviderAdapter para interactuar con Gemini.
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


class GeminiAdapter(ProviderAdapter):
    """Adapter para Gemini API."""

    name = "gemini"

    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(
        self,
        http_client: HTTPClient,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 30.0,
        default_model: Optional[str] = None,
    ):
        super().__init__(http_client, api_key, base_url, timeout)
        self.default_model = default_model or self.DEFAULT_MODEL

    def _build_payload(self, request: ChatRequest) -> dict:
        contents = []
        for msg in request.messages:
            role = msg.role
            if role == "system":
                role = "user"
            normalized_role = "user" if role == "user" else "model"
            contents.append({"role": normalized_role, "parts": [{"text": msg.content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        return payload

    def _get_headers(self) -> dict[str, str]:
        headers = super()._get_headers()
        headers.pop("Authorization", None)
        headers["x-goog-api-key"] = self.api_key
        return headers

    def _extract_text_from_data(self, data: dict) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts if isinstance(part, dict))

    async def stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        request.stream = True
        payload = self._build_payload(request)
        model = request.model or self.default_model
        url = f"{self.base_url}/models/{model}:streamGenerateContent"
        headers = self._get_headers()

        try:
            async for chunk_bytes in self.http_client.stream_post(
                url=url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            ):
                chunk_text = chunk_bytes.decode("utf-8")

                for line in chunk_text.splitlines():
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]
                    else:
                        data_str = line

                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    text = self._extract_text_from_data(data)
                    if text:
                        yield text

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))
        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con Gemini: {str(e)}",
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
        model = request.model or self.default_model
        url = f"{self.base_url}/models/{model}:generateContent"
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

            text = self._extract_text_from_data(data)
            if text:
                usage = data.get("usageMetadata", {})
                prompt_tokens = usage.get("promptTokenCount", 0)
                completion_tokens = usage.get("candidatesTokenCount", 0)
                provider_meta = {
                    "tokens_prompt": prompt_tokens,
                    "tokens_completion": completion_tokens,
                    "tokens_total": prompt_tokens + completion_tokens,
                }

                return ChatResponse(
                    text=text,
                    provider=self.name,
                    model=model,
                    provider_meta=provider_meta,
                )

            raise ProviderError(
                provider=self.name,
                code="INVALID_RESPONSE",
                message="Respuesta de Gemini no contiene texto generado",
                retriable=False,
            )

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e.response.status_code, str(e))
        except httpx.TimeoutException as e:
            raise ProviderError(
                provider=self.name,
                code="TIMEOUT",
                message=f"Timeout al conectar con Gemini: {str(e)}",
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
