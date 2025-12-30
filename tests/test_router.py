"""
Tests para el Router.
"""

import pytest
from unittest.mock import AsyncMock
from typing import AsyncGenerator

from api.router import Router
from api.schemas import ChatRequest, ChatResponse, ProviderError, Message
from api.providers.base import ProviderAdapter


class MockProvider(ProviderAdapter):
    """Mock de proveedor para tests."""

    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.stream_called = False
        self.generate_called = False

    async def stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        self.stream_called = True

        if self.should_fail:
            raise ProviderError(
                provider=self.name,
                code="TEST_ERROR",
                message="Error de prueba",
                retriable=True,
            )

        # Simular stream exitoso
        for i in range(3):
            yield f"chunk{i}"

    async def generate(self, request: ChatRequest) -> ChatResponse:
        self.generate_called = True

        if self.should_fail:
            raise ProviderError(
                provider=self.name,
                code="TEST_ERROR",
                message="Error de prueba",
                retriable=True,
            )

        return ChatResponse(text="Test response", provider=self.name, provider_meta={})


@pytest.fixture
def mock_redis():
    """Fixture de Redis mock."""
    redis = AsyncMock()
    redis.is_provider_blacklisted = AsyncMock(return_value=False)
    redis.increment_failure_count = AsyncMock(return_value=1)
    redis.reset_failure_count = AsyncMock()
    redis.blacklist_provider = AsyncMock()
    return redis


@pytest.fixture
def sample_request():
    """Fixture de ChatRequest de prueba."""
    return ChatRequest(
        messages=[Message(role="user", content="Hola")], max_tokens=100, temperature=0.0
    )


@pytest.mark.asyncio
async def test_router_success_first_provider(mock_redis, sample_request):
    """Test: router usa el primer proveedor exitosamente."""
    provider1 = MockProvider("provider1")
    provider2 = MockProvider("provider2")

    router = Router(
        providers=[provider1, provider2],
        redis_client=mock_redis,
        first_chunk_timeout=1.0,
    )

    chunks = []
    async for chunk in router.choose_and_stream(sample_request, "test-req-1"):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks == ["chunk0", "chunk1", "chunk2"]
    assert provider1.stream_called
    assert not provider2.stream_called


@pytest.mark.asyncio
async def test_router_fallback_to_second_provider(mock_redis, sample_request):
    """Test: router hace fallback al segundo proveedor si el primero falla."""
    provider1 = MockProvider("provider1", should_fail=True)
    provider2 = MockProvider("provider2", should_fail=False)

    router = Router(
        providers=[provider1, provider2],
        redis_client=mock_redis,
        first_chunk_timeout=1.0,
    )

    chunks = []
    async for chunk in router.choose_and_stream(sample_request, "test-req-2"):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert provider1.stream_called
    assert provider2.stream_called

    # Verificar que el primer proveedor fue marcado como fallido
    mock_redis.increment_failure_count.assert_called()
    mock_redis.blacklist_provider.assert_called()


@pytest.mark.asyncio
async def test_router_all_providers_fail(mock_redis, sample_request):
    """Test: router lanza error si todos los proveedores fallan."""
    provider1 = MockProvider("provider1", should_fail=True)
    provider2 = MockProvider("provider2", should_fail=True)

    router = Router(
        providers=[provider1, provider2],
        redis_client=mock_redis,
        first_chunk_timeout=1.0,
    )

    with pytest.raises(ProviderError) as exc_info:
        async for _ in router.choose_and_stream(sample_request, "test-req-3"):
            pass

    assert exc_info.value.code == "ALL_PROVIDERS_FAILED"


@pytest.mark.asyncio
async def test_router_skip_blacklisted_provider(mock_redis, sample_request):
    """Test: router salta proveedores blacklisted."""
    provider1 = MockProvider("provider1")
    provider2 = MockProvider("provider2")

    # Simular que provider1 está blacklisted
    async def mock_is_blacklisted(provider_name: str) -> bool:
        return provider_name == "provider1"

    mock_redis.is_provider_blacklisted = mock_is_blacklisted

    router = Router(
        providers=[provider1, provider2],
        redis_client=mock_redis,
        first_chunk_timeout=1.0,
    )

    chunks = []
    async for chunk in router.choose_and_stream(sample_request, "test-req-4"):
        chunks.append(chunk)

    assert not provider1.stream_called
    assert provider2.stream_called


@pytest.mark.asyncio
async def test_router_generate_success(mock_redis, sample_request):
    """Test: router.choose_and_generate funciona correctamente."""
    provider1 = MockProvider("provider1")

    router = Router(providers=[provider1], redis_client=mock_redis)

    response = await router.choose_and_generate(sample_request, "test-req-5")

    assert response.text == "Test response"
    assert response.provider == "provider1"
    assert provider1.generate_called
