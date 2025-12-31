import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.config import settings


class DummyOrch:
    async def generate_response(self, request, request_id):
        from api.schemas import ChatResponse

        return ChatResponse(text="ok", provider="mock", model="gpt")

    def stream_response(self, request, request_id):
        async def gen():
            yield "chunk"

        return gen()


@pytest.mark.asyncio
async def test_chat_endpoint_valid(monkeypatch):
    transport = ASGITransport(app=app)
    # establecer el estado de los proveedores para la aplicación
    # (algunas pruebas esperan que esté presente)
    # deshabilitar la validación de la clave de la API para las pruebas
    settings.api_key = None
    app.state.providers = []

    # Proveer un orchestrator mock para que la ruta funcione
    class DummyOrch:
        async def generate_response(self, request, request_id):
            from api.schemas import ChatResponse

            return ChatResponse(text="ok", provider="mock", model="gpt")

        async def stream_response(self, request, request_id):
            async def gen():
                yield "chunk"

            return gen()

    app.state.orchestrator = DummyOrch()
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"model": "gpt-3", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stream_endpoint(monkeypatch):
    transport = ASGITransport(app=app)
    settings.api_key = None
    app.state.providers = []
    app.state.orchestrator = DummyOrch()
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/stream",
            json={"model": "gpt-3", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
def test_chat_endpoint_unauthorized():
    transport = ASGITransport(app=app)
    # Forzar que settings.api_key tenga valor
    settings.api_key = "testkey"
    app.state.providers = []
    app.state.orchestrator = DummyOrch()

    async def run():
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/chat",
                json={
                    "model": "gpt-3",
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            assert resp.status_code == 401

    import asyncio

    asyncio.run(run())


@pytest.mark.asyncio
def test_stream_endpoint_error_handling():
    transport = ASGITransport(app=app)
    settings.api_key = None
    app.state.providers = []

    class FailingOrch:
        def stream_response(self, request, request_id):
            async def gen():
                raise Exception("fail")
                yield "chunk"

            return gen()

    app.state.orchestrator = FailingOrch()

    async def run():
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/stream",
                json={
                    "model": "gpt-3",
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            assert resp.status_code == 200
            assert "INTERNAL_ERROR" in resp.text or "fail" in resp.text

    import asyncio

    asyncio.run(run())


@pytest.mark.asyncio
def test_chat_endpoint_forbidden(monkeypatch):
    from fastapi.testclient import TestClient
    from api.main import app

    # Simular settings.api_key y token incorrecto
    from api.config import settings

    settings.api_key = "secret"
    client = TestClient(app)
    app.state.providers = []
    app.state.orchestrator = DummyOrch()
    resp = client.post(
        "/chat",
        json={"model": "gpt-3", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": "Bearer wrong"},
    )
    assert resp.status_code == 401
    assert "API key inválida" in resp.text


@pytest.mark.asyncio
def test_chat_endpoint_missing_auth(monkeypatch):
    from fastapi.testclient import TestClient
    from api.main import app
    from api.config import settings

    settings.api_key = "secret"
    client = TestClient(app)
    app.state.providers = []
    app.state.orchestrator = DummyOrch()
    resp = client.post(
        "/chat",
        json={"model": "gpt-3", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401
    assert "Falta header Authorization" in resp.text


@pytest.mark.asyncio
def test_chat_endpoint_invalid_format(monkeypatch):
    from fastapi.testclient import TestClient
    from api.main import app
    from api.config import settings

    settings.api_key = "secret"
    client = TestClient(app)
    app.state.providers = []
    app.state.orchestrator = DummyOrch()
    resp = client.post(
        "/chat",
        json={"model": "gpt-3", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": "Token secret"},
    )
    assert resp.status_code == 401
    assert "Formato de Authorization inválido" in resp.text
