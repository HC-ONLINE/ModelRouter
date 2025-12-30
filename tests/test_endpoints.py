"""
Tests de integración end-to-end para endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from api.main import app


@pytest.fixture
async def client():
    """Fixture de cliente HTTP async."""
    # Mock del state para evitar que el lifespan se ejecute
    app.state.providers = []
    app.state.redis_client = AsyncMock()
    
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test: endpoint /health responde correctamente."""
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "version" in data
    assert "providers" in data


@pytest.mark.asyncio
async def test_chat_endpoint_unauthorized(client):
    """Test: /chat requiere autorización."""
    # Configurar API key en settings
    from api.config import settings
    original_key = settings.api_key
    settings.api_key = "test-secret-key"
    
    try:
        response = await client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hola"}],
                "max_tokens": 100
            }
        )
        
        assert response.status_code == 401
    finally:
        settings.api_key = original_key


@pytest.mark.asyncio
async def test_chat_endpoint_invalid_request(client):
    """Test: /chat valida el request."""
    response = await client.post(
        "/chat",
        json={
            "messages": [],  # Lista vacía, inválida
            "max_tokens": 100
        }
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """Test: endpoint /metrics responde."""
    response = await client.get("/metrics")
    
    assert response.status_code == 200
    # Verificar que contiene métricas Prometheus
    assert b"modelrouter_requests_total" in response.content
