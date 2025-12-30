"""
Tests para Orchestrator.
"""
import pytest
from unittest.mock import AsyncMock
import asyncio

from api.orchestrator import Orchestrator
from api.router import Router
from api.schemas import ChatRequest, ChatResponse, ProviderError, Message


@pytest.fixture
def sample_request():
    """Fixture de ChatRequest de prueba."""
    return ChatRequest(
        messages=[Message(role="user", content="Test")],
        max_tokens=100,
        temperature=0.0
    )


@pytest.mark.asyncio
async def test_orchestrator_stream_success(sample_request):
    """Test: orchestrator coordina stream correctamente."""
    mock_router = AsyncMock(spec=Router)
    
    async def mock_stream(request, request_id):
        for i in range(3):
            yield f"chunk{i}"
    
    mock_router.choose_and_stream = mock_stream
    
    orchestrator = Orchestrator(
        router=mock_router,
        max_operation_timeout=10.0
    )
    
    chunks = []
    async for chunk in orchestrator.stream_response(sample_request, "test-req"):
        chunks.append(chunk)
    
    assert len(chunks) == 3
    assert chunks == ["chunk0", "chunk1", "chunk2"]


@pytest.mark.asyncio
async def test_orchestrator_stream_timeout(sample_request):
    """Test: orchestrator aplica timeout global en streaming."""
    mock_router = AsyncMock(spec=Router)
    
    async def slow_stream(request, request_id):
        await asyncio.sleep(2.0)  # Simular operación lenta
        yield "chunk"
    
    mock_router.choose_and_stream = slow_stream
    
    orchestrator = Orchestrator(
        router=mock_router,
        max_operation_timeout=0.1  # Timeout muy corto
    )
    
    with pytest.raises(ProviderError) as exc_info:
        async for _ in orchestrator.stream_response(sample_request, "test-req"):
            pass
    
    assert exc_info.value.code == "GLOBAL_TIMEOUT"


@pytest.mark.asyncio
async def test_orchestrator_generate_success(sample_request):
    """Test: orchestrator coordina generación correctamente."""
    mock_router = AsyncMock(spec=Router)
    mock_router.choose_and_generate = AsyncMock(
        return_value=ChatResponse(
            text="Generated text",
            provider="test_provider",
            provider_meta={}
        )
    )
    
    orchestrator = Orchestrator(
        router=mock_router,
        max_operation_timeout=10.0
    )
    
    response = await orchestrator.generate_response(sample_request, "test-req")
    
    assert response.text == "Generated text"
    assert response.provider == "test_provider"


@pytest.mark.asyncio
async def test_orchestrator_generate_timeout(sample_request):
    """Test: orchestrator aplica timeout global en generación."""
    mock_router = AsyncMock(spec=Router)
    
    async def slow_generate(request, request_id):
        await asyncio.sleep(2.0)
        return ChatResponse(text="text", provider="test", provider_meta={})
    
    mock_router.choose_and_generate = slow_generate
    
    orchestrator = Orchestrator(
        router=mock_router,
        max_operation_timeout=0.1
    )
    
    with pytest.raises(ProviderError) as exc_info:
        await orchestrator.generate_response(sample_request, "test-req")
    
    assert exc_info.value.code == "GLOBAL_TIMEOUT"
