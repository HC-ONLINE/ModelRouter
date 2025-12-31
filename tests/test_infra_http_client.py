import pytest
from api.infra.http_client import HTTPClient
from unittest.mock import AsyncMock, MagicMock
import httpx


@pytest.mark.asyncio
async def test_http_client_post(monkeypatch):
    client = HTTPClient()
    # Mock de httpx.AsyncClient
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.aclose = AsyncMock()
    client.client = AsyncMock(spec=httpx.AsyncClient)
    client.client.post.return_value = mock_response
    resp = await client.post("http://x", json={})
    assert resp.status_code == 200
    await resp.aclose()


@pytest.mark.asyncio
async def test_http_client_stream_post(monkeypatch):
    client = HTTPClient()
    # Mock de httpx.AsyncClient para streaming
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.raise_for_status = MagicMock()

    async def aiter_bytes():
        yield b"data"

    mock_response.aiter_bytes = aiter_bytes

    # Mock del contexto async para stream
    class DummyStream:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, exc_type, exc, tb):
            pass

    client.client = AsyncMock(spec=httpx.AsyncClient)
    client.client.stream.return_value = DummyStream()
    gen = client.stream_post("http://x", json={})
    data = [chunk async for chunk in gen]
    assert data == [b"data"]
