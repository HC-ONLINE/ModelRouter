from fastapi.testclient import TestClient
from api.main import app


def test_health_endpoint_status(monkeypatch):
    client = TestClient(app)
    # Mock providers y redis_client
    app.state.providers = [type("P", (), {"name": "prov1"})()]

    class DummyRedis:
        async def is_provider_blacklisted(self, name):
            return False

    app.state.redis_client = DummyRedis()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_metrics_endpoint(monkeypatch):
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200


def test_global_exception_handler():
    from fastapi.responses import JSONResponse
    from starlette.requests import Request as StarletteRequest
    from starlette.types import Scope
    import asyncio
    from api.main import global_exception_handler

    # Crear un scope mínimo para Request
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
        "app": app,
        "http_version": "1.1",
    }
    req = StarletteRequest(scope)
    resp = asyncio.run(global_exception_handler(req, Exception("fail")))
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 500
    # resp.body puede ser bytes o memoryview
    body_bytes = resp.body.tobytes() if isinstance(resp.body, memoryview) else resp.body
    assert "INTERNAL_ERROR" in body_bytes.decode()
