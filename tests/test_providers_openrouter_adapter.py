import pytest

from api.providers.openrouter_adapter import OpenRouterAdapter
from api.schemas import ChatRequest, Message
from api.infra.http_client import HTTPClient
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_openrouter_stream(monkeypatch):
    # Mock HTTPClient
    mock_http_client = AsyncMock(spec=HTTPClient)

    async def mock_stream_post(*args, **kwargs):
        yield b'data: {"choices": [{"delta": {"content": "hi"}}]}'

    mock_http_client.stream_post.side_effect = mock_stream_post
    adapter = OpenRouterAdapter(
        http_client=mock_http_client, api_key="key", base_url="http://test"
    )
    req = ChatRequest(messages=[Message(role="user", content="hi")], model="gpt-3")
    monkeypatch.setattr(adapter, "_get_headers", lambda: {"Authorization": "Bearer x"})
    gen = adapter.stream(req)
    chunk = await anext(gen)
    assert isinstance(chunk, str)


@pytest.mark.asyncio
async def test_openrouter_generate(monkeypatch):
    # Mock HTTPClient
    mock_http_client = AsyncMock(spec=HTTPClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "hi"}}]}
    mock_response.aclose = AsyncMock()
    mock_http_client.post.return_value = mock_response
    adapter = OpenRouterAdapter(
        http_client=mock_http_client, api_key="key", base_url="http://test"
    )
    req = ChatRequest(messages=[Message(role="user", content="hi")], model="gpt-3")
    monkeypatch.setattr(adapter, "_get_headers", lambda: {"Authorization": "Bearer x"})
    resp = await adapter.generate(req)
    assert hasattr(resp, "text")
