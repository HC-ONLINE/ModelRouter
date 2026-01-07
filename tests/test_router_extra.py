import pytest


from api.router import Router
from api.providers.base import ProviderAdapter
from api.schemas import ChatRequest, Message, ChatResponse
from api.infra.http_client import HTTPClient
from api.infra.redis_client import RedisClient
from api.config import Settings
from unittest.mock import AsyncMock


class DummyRedis(AsyncMock, RedisClient):
    async def increment_failure_count(self, provider):
        return 1

    async def blacklist_provider(self, provider, seconds):
        return None

    async def is_provider_blacklisted(self, provider):
        return False

    async def reset_failure_count(self, provider):
        return None

    async def check_provider_rate_limit(
        self, provider_name: str, user_id: str, max_requests: int, window_seconds: int
    ):
        return (True, max_requests - 1)


class AlwaysFailProvider(ProviderAdapter):
    async def stream(self, request: ChatRequest):
        raise Exception("fail")
        yield  # para que sea un async generator

    async def generate(self, request: ChatRequest):
        raise Exception("fail")


@pytest.mark.asyncio
async def test_router_all_failures(monkeypatch):
    mock_http = AsyncMock(spec=HTTPClient)
    settings = Settings()
    router = Router(
        [AlwaysFailProvider(mock_http, "k", "u")], DummyRedis(), settings=settings
    )
    req = ChatRequest(messages=[Message(role="user", content="hi")], model="gpt-3")
    with pytest.raises(Exception):
        await anext(router.choose_and_stream(req, "id"))


@pytest.mark.asyncio
async def test_router_success(monkeypatch):
    class OkProvider(ProviderAdapter):
        async def stream(self, request: ChatRequest):
            yield "ok"

        async def generate(self, request: ChatRequest):
            return ChatResponse(text="ok", provider="ok")

    mock_http = AsyncMock(spec=HTTPClient)
    settings = Settings()
    router = Router([OkProvider(mock_http, "k", "u")], DummyRedis(), settings=settings)
    req = ChatRequest(messages=[Message(role="user", content="hi")], model="gpt-3")
    result = await anext(router.choose_and_stream(req, "id"))
    assert result == "ok"
