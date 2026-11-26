"""Go4Guru Modular Monolith FastAPI Application Entrypoint (Phase 0)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.config import Settings, get_settings
from src.core.database import DatabaseManager
from src.core.errors import register_exception_handlers
from src.core.health import router as health_router
from src.core.logging import configure_logging
from src.core.middleware import RequestContextAndSecurityMiddleware
from src.core.redis_client import RedisManager
from src.modules import DOMAIN_MODULES
from src.modules.ai.public import ai_admin_router, ai_router
from src.modules.analytics.public import analytics_router
from src.modules.assessment.public import (
    assessments_router,
    bookmarks_router,
    notes_router,
    practice_router,
    quizzes_router,
)
from src.modules.classroom.public import (
    classroom_router,
    classroom_ws_router,
    languages_router,
    voice_router,
    whiteboard_router,
)
from src.modules.content.public import rights_router
from src.modules.curriculum.public import curriculum_router
from src.modules.identity.public import admin_identity_router, auth_router, users_router
from src.modules.learning.public import dashboard_router, learning_router
from src.modules.notifications.public import notifications_router
from src.modules.question_bank.public import imports_router, questions_router
from src.modules.revision.public import revision_router

logger = logging.getLogger("go4guru.app")


class ModuleBoundaryInfo(BaseModel):
    """Describes a registered modular-monolith domain and its rollout phase."""

    name: str
    status: str
    planned_phase: str


class ApiMetaResponse(BaseModel):
    """Platform metadata endpoint for Phase 0 architecture verification."""

    service: str
    version: str
    environment: str
    api_prefix: str
    ws_prefix: str
    phase: str
    modules: list[ModuleBoundaryInfo]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and cleanly dispose core database and Redis managers."""
    settings: Settings = app.state.settings
    configure_logging(level=settings.log_level, log_format=settings.log_format)

    db = DatabaseManager(settings=settings)
    redis = RedisManager(settings=settings)
    app.state.db = db
    app.state.redis = redis

    logger.info("Go4Guru API Phase 0 lifespan started", extra={"event": "startup"})
    try:
        yield
    finally:
        await redis.close()
        await db.dispose()
        logger.info("Go4Guru API Phase 0 lifespan stopped", extra={"event": "shutdown"})


def create_app(settings_override: Settings | None = None) -> FastAPI:
    """Construct the FastAPI application with versioned boundaries and security baseline."""
    settings = settings_override or get_settings()

    application = FastAPI(
        title="Go4Guru Platform API",
        version=settings.app_version,
        description=(
            "Multilingual AI Learning Ecosystem API (Phase 0 Foundation). "
            "Domain endpoints activate progressively in Phases 1-12."
        ),
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        lifespan=lifespan,
    )
    application.state.settings = settings

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(RequestContextAndSecurityMiddleware)
    register_exception_handlers(application)

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(admin_identity_router)
    application.include_router(rights_router)
    application.include_router(curriculum_router)
    application.include_router(questions_router)
    application.include_router(imports_router)
    application.include_router(practice_router)
    application.include_router(quizzes_router)
    application.include_router(assessments_router)
    application.include_router(notes_router)
    application.include_router(bookmarks_router)
    application.include_router(dashboard_router)
    application.include_router(learning_router)
    application.include_router(revision_router)
    application.include_router(notifications_router)
    application.include_router(analytics_router)
    application.include_router(ai_router)
    application.include_router(ai_admin_router)
    application.include_router(languages_router)
    application.include_router(classroom_router)
    application.include_router(whiteboard_router)
    application.include_router(voice_router)

    api_v1 = APIRouter(prefix="/api/v1", tags=["v1"])

    @api_v1.get("/meta", response_model=ApiMetaResponse)
    async def api_meta() -> ApiMetaResponse:
        """Return API versioning, Phase 4 active domain registry, and rollout status."""
        return ApiMetaResponse(
            service=settings.app_name,
            version=settings.app_version,
            environment=settings.app_env,
            api_prefix="/api/v1",
            ws_prefix="/ws/v1",
            phase="phase_5_adaptive_learning_and_revision",
            modules=[
                ModuleBoundaryInfo(
                    name=descriptor.name,
                    status=descriptor.status,
                    planned_phase=descriptor.planned_phase,
                )
                for descriptor in DOMAIN_MODULES
            ],
        )

    application.include_router(api_v1)

    @application.websocket("/ws/v1/classroom/status")
    async def classroom_ws_status(websocket: WebSocket) -> None:
        """Report Live AI Classroom WebSocket availability."""
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "ONLINE",
                "phase": "phase_4",
                "message": "Live AI Classroom WebSocket active at /ws/v1/classroom/{session_id}.",
            }
        )
        try:
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
        except WebSocketDisconnect:
            return

    application.include_router(classroom_ws_router)

    return application


app = create_app()
