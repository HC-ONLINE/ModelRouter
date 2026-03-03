import pytest
from unittest.mock import AsyncMock, MagicMock

from api.providers.openai_adapter import OpenAIAdapter
from api.schemas import ChatRequest, Message
from api.infra.http_client import HTTPClient


@pytest.mark.asyncio
async def test_openai_stream(monkeypatch):
    # Mock HTTPClient
    mock_http_client = AsyncMock(spec=HTTPClient)

    async def mock_stream_post(*args, **kwargs):
        yield b'data: {"choices": [{"delta": {"content": "hi"}}]}'

    mock_http_client.stream_post.side_effect = mock_stream_post
    adapter = OpenAIAdapter(http_client=mock_http_client, api_key="test_key")
    req = ChatRequest(
        messages=[Message(role="user", content="hi")], model="gpt-4o-mini"
    )
    monkeypatch.setattr(
        adapter, "_get_headers", lambda: {"Authorization": "Bearer test_key"}
    )

    gen = adapter.stream(req)
    chunk = await anext(gen)
    assert chunk == "hi"
    assert isinstance(chunk, str)


@pytest.mark.asyncio
async def test_openai_generate(monkeypatch):
    # Mock HTTPClient
    mock_http_client = AsyncMock(spec=HTTPClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "hi"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    mock_http_client.post.return_value = mock_response

    adapter = OpenAIAdapter(http_client=mock_http_client, api_key="test_key")
    req = ChatRequest(
        messages=[Message(role="user", content="hi")], model="gpt-4o-mini"
    )
    monkeypatch.setattr(
        adapter, "_get_headers", lambda: {"Authorization": "Bearer test_key"}
    )

    resp = await adapter.generate(req)
    assert resp.text == "hi"
    assert resp.provider == "openai"
    assert resp.provider_meta["tokens_total"] == 15
