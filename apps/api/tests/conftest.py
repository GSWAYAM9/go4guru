"""Shared pytest fixtures for Go4Guru API Phase 0 tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from src.core.config import Settings
from src.main import create_app


class StubCheck:
    """Deterministic stub for DB/Redis connectivity checks in API tests."""

    def __init__(self, *, healthy: bool, error: str | None = None) -> None:
        self.healthy = healthy
        self.error = error

    async def check_connectivity(self) -> tuple[bool, str | None]:
        return self.healthy, self.error

    async def close(self) -> None:
        return None

    async def dispose(self) -> None:
        return None


@pytest.fixture
def test_settings() -> Settings:
    """Return isolated test settings without requiring live credentials."""
    return Settings(
        app_env="test",
        log_level="INFO",
        log_format="json",
        jwt_secret_key="test-only-jwt-secret-key-with-more-than-32-chars",
        cors_allowed_origins=["http://localhost:3000"],
    )


@pytest.fixture
def api_app(test_settings: Settings):
    """Create a FastAPI app prewired with healthy stub dependency probes."""
    app = create_app(settings_override=test_settings)
    app.state.db = StubCheck(healthy=True, error=None)
    app.state.redis = StubCheck(healthy=True, error=None)
    return app


@pytest.fixture
async def async_client(api_app) -> AsyncClient:
    """HTTPX AsyncClient targeting ASGI app directly (skipping real socket lifespan)."""
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
