"""Liveness and dependency-backed readiness endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from src.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class DependencyStatus(BaseModel):
    """Observed status of a single runtime dependency."""

    status: Literal["up", "down"]
    error: str | None = None


class LivenessResponse(BaseModel):
    """Response schema for process liveness."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str
    phase: str
    timestamp: str


class ReadinessResponse(BaseModel):
    """Response schema for dependency-backed readiness."""

    status: Literal["ready", "degraded"]
    service: str
    version: str
    environment: str
    phase: str
    checks: dict[str, DependencyStatus]
    timestamp: str


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def evaluate_readiness(request: Request) -> tuple[int, ReadinessResponse]:
    """Probe PostgreSQL and Redis honestly; return 503 if any core dependency is down."""
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    db = request.app.state.db
    redis = request.app.state.redis

    db_ok, db_err = await db.check_connectivity()
    redis_ok, redis_err = await redis.check_connectivity()

    all_ready = db_ok and redis_ok
    payload = ReadinessResponse(
        status="ready" if all_ready else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        phase="phase_5_adaptive_learning_and_revision",
        checks={
            "postgres": DependencyStatus(status="up" if db_ok else "down", error=db_err),
            "redis": DependencyStatus(status="up" if redis_ok else "down", error=redis_err),
        },
        timestamp=_utc_now_iso(),
    )
    http_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return http_code, payload


@router.get("/health/live", response_model=LivenessResponse)
@router.get("/api/v1/health/live", response_model=LivenessResponse)
async def liveness(request: Request) -> LivenessResponse:
    """Confirm the API process is alive without claiming downstream readiness."""
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return LivenessResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        phase="phase_5_adaptive_learning_and_revision",
        timestamp=_utc_now_iso(),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
@router.get(
    "/api/v1/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    """Check PostgreSQL and Redis connectivity and return 503 if any check fails."""
    code, payload = await evaluate_readiness(request)
    response.status_code = code
    return payload
