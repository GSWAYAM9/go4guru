"""API tests for health/readiness probes, versioning, security headers, and error envelopes."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from src.core.errors import AppError
from src.modules import DOMAIN_MODULES

from tests.conftest import StubCheck


async def test_liveness_endpoints_return_200_and_security_headers(
    async_client: AsyncClient,
) -> None:
    for path in ("/health/live", "/api/v1/health/live"):
        response = await async_client.get(path, headers={"X-Request-ID": "trace-live-1"})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["phase"] == "phase_5_adaptive_learning_and_revision"
        assert response.headers["X-Request-ID"] == "trace-live-1"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"


async def test_readiness_returns_200_when_postgres_and_redis_healthy(
    async_client: AsyncClient,
) -> None:
    for path in ("/health/ready", "/api/v1/health/ready"):
        response = await async_client.get(path)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["checks"]["postgres"] == {"status": "up", "error": None}
        assert body["checks"]["redis"] == {"status": "up", "error": None}


@pytest.mark.parametrize(
    ("db_ok", "db_err", "redis_ok", "redis_err"),
    [
        (False, "ConnectionRefusedError", True, None),
        (True, None, False, "TimeoutError"),
        (False, "OperationalError", False, "ConnectionError"),
    ],
)
async def test_readiness_returns_503_when_any_dependency_is_down(
    api_app,
    db_ok: bool,
    db_err: str | None,
    redis_ok: bool,
    redis_err: str | None,
) -> None:
    api_app.state.db = StubCheck(healthy=db_ok, error=db_err)
    api_app.state.redis = StubCheck(healthy=redis_ok, error=redis_err)

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["postgres"]["status"] == ("up" if db_ok else "down")
    assert body["checks"]["redis"]["status"] == ("up" if redis_ok else "down")


async def test_api_v1_meta_lists_all_16_domain_modules(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["api_prefix"] == "/api/v1"
    assert body["ws_prefix"] == "/ws/v1"
    returned_names = {m["name"] for m in body["modules"]}
    expected_names = {d.name for d in DOMAIN_MODULES}
    assert len(returned_names) == 16
    assert returned_names == expected_names


async def test_http_404_and_invalid_request_id_sanitization(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get(
        "/api/v1/nonexistent-route",
        headers={"X-Request-ID": "bad\nheader\tinjection"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "HTTP_404"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "bad\n" not in response.headers["X-Request-ID"]


async def test_app_error_and_openapi_versioned_endpoint(api_app) -> None:
    @api_app.get("/api/v1/_test-error")
    async def trigger_error() -> None:
        raise AppError(status_code=400, code="BAD_TEST", message="Invalid test input")

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        err_resp = await client.get("/api/v1/_test-error", headers={"X-Request-ID": "req-400"})
        assert err_resp.status_code == 400
        assert err_resp.json() == {
            "error": {
                "code": "BAD_TEST",
                "message": "Invalid test input",
                "details": None,
                "request_id": "req-400",
            }
        }

        openapi_resp = await client.get("/api/v1/openapi.json")
        assert openapi_resp.status_code == 200
        assert openapi_resp.json()["info"]["title"] == "Go4Guru Platform API"
