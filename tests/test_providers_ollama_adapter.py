"""
Tests para OllamaAdapter.
"""

import pytest

from api.providers.ollama_adapter import OllamaAdapter
from api.schemas import ChatRequest, Message
from api.infra.http_client import HTTPClient
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_ollama_stream(monkeypatch):
    """Test: OllamaAdapter streamea correctamente."""
    # Mock HTTPClient
    mock_http_client = AsyncMock(spec=HTTPClient)

    async def mock_stream_post(*args, **kwargs):
        # Simular respuesta de Ollama /api/generate en formato JSON line-delimited
        yield b'{"response": "Hola"}\n'
        yield b'{"response": " mundo"}\n'
        yield b'{"response": "!", "done": true}\n'

    mock_http_client.stream_post.side_effect = mock_stream_post
    adapter = OllamaAdapter(
        http_client=mock_http_client, api_key="", base_url="http://localhost:11434"
    )
    req = ChatRequest(messages=[Message(role="user", content="test")], model="llama3.2")

    chunks = []
    async for chunk in adapter.stream(req):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0] == "Hola"
    assert chunks[1] == " mundo"
    assert chunks[2] == "!"


@pytest.mark.asyncio
async def test_ollama_generate(monkeypatch):
    """Test: OllamaAdapter genera respuesta completa correctamente."""
    # Mock HTTPClient
    mock_http_client = AsyncMock(spec=HTTPClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "response": "Respuesta completa",
        "model": "llama3.2",
        "done": True,
        "total_duration": 1000000,
        "prompt_eval_count": 10,
        "eval_count": 20,
    }
    mock_response.aclose = AsyncMock()
    mock_http_client.post.return_value = mock_response

    adapter = OllamaAdapter(
        http_client=mock_http_client, api_key="", base_url="http://localhost:11434"
    )
    req = ChatRequest(messages=[Message(role="user", content="test")], model="llama3.2")

    resp = await adapter.generate(req)

    assert hasattr(resp, "text")
    assert resp.text == "Respuesta completa"
    assert resp.provider == "ollama"
    assert resp.model == "llama3.2"


@pytest.mark.asyncio
async def test_ollama_stream_empty_content():
    """Test: OllamaAdapter maneja chunks vacíos correctamente."""
    mock_http_client = AsyncMock(spec=HTTPClient)

    async def mock_stream_post(*args, **kwargs):
        yield b'{"response": ""}\n'
        yield b'{"response": "texto"}\n'
        yield b'{"done": true}\n'

    mock_http_client.stream_post.side_effect = mock_stream_post
    adapter = OllamaAdapter(
        http_client=mock_http_client, api_key="", base_url="http://localhost:11434"
    )
    req = ChatRequest(messages=[Message(role="user", content="test")])

    chunks = []
    async for chunk in adapter.stream(req):
        chunks.append(chunk)

    # Solo debe capturar el chunk con contenido
    assert len(chunks) == 1
    assert chunks[0] == "texto"


@pytest.mark.asyncio
async def test_ollama_headers_without_api_key():
    """Test: OllamaAdapter no incluye Authorization si no hay API key."""
    mock_http_client = AsyncMock(spec=HTTPClient)
    adapter = OllamaAdapter(
        http_client=mock_http_client, api_key="", base_url="http://localhost:11434"
    )

    headers = adapter._get_headers()

    assert "Content-Type" in headers
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_ollama_headers_with_api_key():
    """Test: OllamaAdapter incluye Authorization si hay API key."""
    mock_http_client = AsyncMock(spec=HTTPClient)
    adapter = OllamaAdapter(
        http_client=mock_http_client,
        api_key="test_key",
        base_url="http://localhost:11434",
    )

    headers = adapter._get_headers()

    assert "Content-Type" in headers
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test_key"


@pytest.mark.asyncio
async def test_ollama_build_payload():
    """Test: OllamaAdapter construye el payload correctamente."""
    mock_http_client = AsyncMock(spec=HTTPClient)
    adapter = OllamaAdapter(
        http_client=mock_http_client, api_key="", base_url="http://localhost:11434"
    )

    req = ChatRequest(
        messages=[Message(role="user", content="test")],
        model="llama3.2",
        max_tokens=100,
        temperature=0.7,
        stream=True,
    )

    payload = adapter._build_payload(req)

    assert payload["model"] == "llama3.2"
    assert payload["stream"]
    assert "prompt" in payload
    assert isinstance(payload["prompt"], str)
    assert "User: test" in payload["prompt"]
    assert payload["options"]["num_predict"] == 100
    assert payload["options"]["temperature"] == 0.7
