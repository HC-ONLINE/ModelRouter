import pytest
from api.providers import base
from api.schemas import ChatRequest


from api.infra.http_client import HTTPClient


from api.schemas import ChatResponse


class DummyAdapter(base.ProviderAdapter):
    def __init__(self):
        super().__init__(http_client=HTTPClient(), api_key="key", base_url="url")

    async def stream(self, request: ChatRequest):
        yield "test"

    async def generate(self, request: ChatRequest):
        return ChatResponse(text="response", provider="dummy")


def test_get_headers():
    adapter = DummyAdapter()
    headers = adapter._get_headers()
    assert isinstance(headers, dict)
    assert "Authorization" in headers


def test_handle_http_error():
    adapter = DummyAdapter()
    err = adapter._handle_http_error(404, "not found")
    # La implementación devuelve códigos como 'HTTP_404' o códigos simbólicos
    assert isinstance(err.code, str)
    assert "404" in err.code or err.code == "BAD_REQUEST"
    assert "not found" in err.message


@pytest.mark.asyncio
async def test_check_health():
    adapter = DummyAdapter()
    result = await adapter._check_health()
    assert isinstance(result, bool)
