"""
Tests para ProviderAdapters.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from api.providers.groq_adapter import GroqAdapter
from api.providers.openrouter_adapter import OpenRouterAdapter
from api.schemas import ChatRequest, ProviderError, Message


@pytest.fixture
def mock_http_client():
    """Fixture de HTTPClient mock."""
    client = AsyncMock()
    return client


@pytest.fixture
def sample_request():
    """Fixture de ChatRequest."""
    return ChatRequest(
        messages=[Message(role="user", content="Hola")], max_tokens=100, temperature=0.5
    )


@pytest.mark.asyncio
async def test_groq_adapter_generate_success(mock_http_client, sample_request):
    """Test: GroqAdapter genera respuesta exitosamente."""
    # Mock de respuesta HTTP
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hola! ¿Cómo estás?"}}],
        "model": "llama-3.3-70b-versatile",
        "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
    }
    mock_response.raise_for_status = MagicMock()

    mock_http_client.post = AsyncMock(return_value=mock_response)

    adapter = GroqAdapter(
        http_client=mock_http_client,
        api_key="test-key",
        base_url="https://api.groq.com/openai/v1",
        timeout=30.0,
    )

    response = await adapter.generate(sample_request)

    assert response.text == "Hola! ¿Cómo estás?"
    assert response.provider == "groq"
    assert response.provider_meta["tokens_total"] == 25


@pytest.mark.asyncio
async def test_groq_adapter_stream_success(mock_http_client, sample_request):
    """Test: GroqAdapter streamea correctamente."""
    # Simular chunks SSE
    sse_data = [
        b'data: {"choices": [{"delta": {"content": "Hola"}}]}\n\n',
        b'data: {"choices": [{"delta": {"content": " mundo"}}]}\n\n',
        b"data: [DONE]\n\n",
    ]

    async def mock_stream(**kwargs):
        for chunk in sse_data:
            yield chunk

    mock_http_client.stream_post = mock_stream

    adapter = GroqAdapter(
        http_client=mock_http_client,
        api_key="test-key",
        base_url="https://api.groq.com/openai/v1",
        timeout=30.0,
    )

    chunks = []
    async for chunk in adapter.stream(sample_request):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert chunks[0] == "Hola"
    assert chunks[1] == " mundo"


@pytest.mark.asyncio
async def test_openrouter_adapter_generate_success(mock_http_client, sample_request):
    """Test: OpenRouterAdapter genera respuesta exitosamente."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Respuesta de OpenRouter"}}],
        "model": "openai/gpt-3.5-turbo",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
    mock_response.raise_for_status = MagicMock()

    mock_http_client.post = AsyncMock(return_value=mock_response)

    adapter = OpenRouterAdapter(
        http_client=mock_http_client,
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        timeout=30.0,
    )

    response = await adapter.generate(sample_request)

    assert response.text == "Respuesta de OpenRouter"
    assert response.provider == "openrouter"


@pytest.mark.asyncio
async def test_adapter_handle_http_error(mock_http_client, sample_request):
    """Test: Adapter maneja errores HTTP correctamente."""
    import httpx

    # Simular error 429 (rate limit)
    mock_response = MagicMock()
    mock_response.status_code = 429

    error = httpx.HTTPStatusError(
        "Rate limit exceeded", request=MagicMock(), response=mock_response
    )

    mock_http_client.post = AsyncMock(side_effect=error)

    adapter = GroqAdapter(
        http_client=mock_http_client,
        api_key="test-key",
        base_url="https://api.groq.com/openai/v1",
        timeout=30.0,
    )

    with pytest.raises(ProviderError) as exc_info:
        await adapter.generate(sample_request)

    assert exc_info.value.code == "RATE_LIMIT"
    assert exc_info.value.retriable is True
