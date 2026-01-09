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
    redis.check_provider_rate_limit = AsyncMock(return_value=(True, 59))
    return redis


@pytest.fixture
def mock_settings():
    """Fixture de Settings mock."""
    from api.config import Settings

    settings = Settings()
    settings.groq_rate_limit = 100
    settings.openrouter_rate_limit = 50
    return settings


@pytest.fixture
def sample_request():
    """Fixture de ChatRequest de prueba."""
    return ChatRequest(
        messages=[Message(role="user", content="Hola")], max_tokens=100, temperature=0.0
    )


@pytest.mark.asyncio
async def test_router_success_first_provider(mock_redis, mock_settings, sample_request):
    """Test: router usa el primer proveedor exitosamente."""
    provider1 = MockProvider("provider1")
    provider2 = MockProvider("provider2")

    router = Router(
        providers=[provider1, provider2],
        redis_client=mock_redis,
        settings=mock_settings,
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
async def test_router_fallback_to_second_provider(
    mock_redis, mock_settings, sample_request
):
    """Test: router hace fallback al segundo proveedor si el primero falla."""
    provider1 = MockProvider("provider1", should_fail=True)
    provider2 = MockProvider("provider2", should_fail=False)

    router = Router(
        providers=[provider1, provider2],
        redis_client=mock_redis,
        settings=mock_settings,
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
async def test_router_all_providers_fail(mock_redis, mock_settings, sample_request):
    """Test: router lanza error si todos los proveedores fallan."""
    provider1 = MockProvider("provider1", should_fail=True)
    provider2 = MockProvider("provider2", should_fail=True)

    router = Router(
        providers=[provider1, provider2],
        redis_client=mock_redis,
        settings=mock_settings,
        first_chunk_timeout=1.0,
    )

    with pytest.raises(ProviderError) as exc_info:
        async for _ in router.choose_and_stream(sample_request, "test-req-3"):
            pass

    assert exc_info.value.code == "ALL_PROVIDERS_FAILED"


@pytest.mark.asyncio
async def test_router_skip_blacklisted_provider(
    mock_redis, mock_settings, sample_request
):
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
        settings=mock_settings,
        first_chunk_timeout=1.0,
    )

    chunks = []
    async for chunk in router.choose_and_stream(sample_request, "test-req-4"):
        chunks.append(chunk)

    assert not provider1.stream_called
    assert provider2.stream_called


@pytest.mark.asyncio
async def test_router_generate_success(mock_redis, mock_settings, sample_request):
    """Test: router.choose_and_generate funciona correctamente."""
    provider1 = MockProvider("provider1")

    router = Router(
        providers=[provider1], redis_client=mock_redis, settings=mock_settings
    )

    response = await router.choose_and_generate(sample_request, "test-req-5")

    assert response.text == "Test response"
    assert response.provider == "provider1"
    assert provider1.generate_called


@pytest.mark.asyncio
async def test_router_respects_provider_rate_limits(
    mock_redis, mock_settings, sample_request
):
    """Test: router respeta rate limits específicos por proveedor."""
    provider1 = MockProvider("groq")
    provider2 = MockProvider("openrouter")

    # Simular que groq ha excedido su rate limit
    async def mock_check_rate_limit(
        provider_name: str, user_id: str, max_requests: int, window_seconds: int
    ):
        if provider_name == "groq":
            return (False, 0)  # Rate limit excedido
        return (True, max_requests - 1)  # Permitido

    mock_redis.check_provider_rate_limit = mock_check_rate_limit

    router = Router(
        providers=[provider1, provider2],
        redis_client=mock_redis,
        settings=mock_settings,
        first_chunk_timeout=1.0,
    )

    chunks = []
    async for chunk in router.choose_and_stream(sample_request, "test-req-6"):
        chunks.append(chunk)

    # groq debería ser saltado por rate limit
    assert not provider1.stream_called
    # openrouter debería ser usado
    assert provider2.stream_called
    assert len(chunks) == 3


@pytest.mark.asyncio
async def test_router_uses_only_specified_provider(
    mock_redis, mock_settings, sample_request
):
    """Test: si se especifica provider, solo ese se usa y no hay fallback."""
    provider1 = MockProvider("groq")
    provider2 = MockProvider("openrouter")

    router = Router(
        providers=[provider1, provider2],
        redis_client=mock_redis,
        settings=mock_settings,
        first_chunk_timeout=1.0,
    )

    req = ChatRequest(
        messages=[Message(role="user", content="Hola")],
        max_tokens=100,
        provider="openrouter",
    )

    chunks = []
    async for chunk in router.choose_and_stream(req, "test-req-provider-specific"):
        chunks.append(chunk)

    assert provider2.stream_called
    assert not provider1.stream_called
    assert chunks == ["chunk0", "chunk1", "chunk2"]


@pytest.mark.asyncio
async def test_router_invalid_provider_raises_error(
    mock_redis, mock_settings, sample_request
):
    """Test: si el provider no existe, lanza ProviderError con code INVALID_PROVIDER."""
    provider1 = MockProvider("groq")
    router = Router(
        providers=[provider1],
        redis_client=mock_redis,
        settings=mock_settings,
        first_chunk_timeout=1.0,
    )
    req = ChatRequest(
        messages=[Message(role="user", content="Hola")],
        max_tokens=100,
        provider="noexiste",
    )
    with pytest.raises(ProviderError) as exc_info:
        async for _ in router.choose_and_stream(req, "test-req-invalid-provider"):
            pass
    assert exc_info.value.code == "INVALID_PROVIDER"


@pytest.mark.asyncio
async def test_router_blacklisted_provider_raises_error(
    mock_redis, mock_settings, sample_request
):
    """Test: si el provider está en blacklist,
    lanza ProviderError con code PROVIDER_UNAVAILABLE."""
    provider1 = MockProvider("groq")
    router = Router(
        providers=[provider1],
        redis_client=mock_redis,
        settings=mock_settings,
        first_chunk_timeout=1.0,
    )

    # Simular que groq está blacklisted
    async def mock_is_blacklisted(provider_name: str) -> bool:
        return provider_name == "groq"

    mock_redis.is_provider_blacklisted = mock_is_blacklisted
    req = ChatRequest(
        messages=[Message(role="user", content="Hola")], max_tokens=100, provider="groq"
    )
    with pytest.raises(ProviderError) as exc_info:
        async for _ in router.choose_and_stream(req, "test-req-blacklisted-provider"):
            pass
    assert exc_info.value.code == "PROVIDER_UNAVAILABLE"
