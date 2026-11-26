"""FastAPI routes for Phase 3 Modular AI Tutor, Hybrid RAG, Cost Telemetry & Evals."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.core.config import Settings, get_settings
from src.modules.ai.evals import list_eval_runs, run_golden_evaluation_suite
from src.modules.ai.orchestrator import AIOrchestratorService
from src.modules.ai.retrieval import ingest_knowledge_document, list_knowledge_documents
from src.modules.ai.schemas import (
    AiCostSummaryResponse,
    AiEvalRunResponse,
    AiFlagMessageRequest,
    AiMessageOut,
    AiModelsCatalogResponse,
    AiModeUpdateRequest,
    AiReviewDecisionRequest,
    AiReviewQueueOut,
    AiSessionCreateRequest,
    AiSessionOut,
    AiTurnRequest,
    AiTurnResponse,
    AiUsageQuotaResponse,
    KnowledgeDocIngestRequest,
    KnowledgeDocOut,
)

ai_router = APIRouter(prefix="/api/v1/ai", tags=["ai-tutor"])
ai_admin_router = APIRouter(prefix="/api/v1/admin", tags=["ai-admin"])


def get_runtime_settings(request: Request) -> Settings:
    """Resolve app.state.settings first so tests overriding settings work deterministically."""
    return getattr(request.app.state, "settings", get_settings())


@ai_router.get("/models", response_model=AiModelsCatalogResponse)
async def get_ai_models_catalog(
    caller: AuthenticatedUser = Depends(require_permissions("ai:chat")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> AiModelsCatalogResponse:
    _ = caller
    return await AIOrchestratorService(db, settings).get_models_catalog()


@ai_router.get("/usage", response_model=AiUsageQuotaResponse)
async def get_ai_usage_quota(
    caller: AuthenticatedUser = Depends(require_permissions("ai:chat")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> AiUsageQuotaResponse:
    return await AIOrchestratorService(db, settings).get_usage_quota(caller)


@ai_router.post("/sessions", response_model=AiSessionOut, status_code=status.HTTP_201_CREATED)
async def create_ai_session(
    payload: AiSessionCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("ai:chat")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> AiSessionOut:
    return await AIOrchestratorService(db, settings).create_session(payload, caller)


@ai_router.get("/sessions", response_model=list[AiSessionOut])
async def list_ai_sessions(
    caller: AuthenticatedUser = Depends(require_permissions("ai:chat")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> list[AiSessionOut]:
    return await AIOrchestratorService(db, settings).list_sessions(caller)


@ai_router.patch("/sessions/{session_id}/mode", response_model=AiSessionOut)
async def update_ai_session_mode(
    session_id: UUID,
    payload: AiModeUpdateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("ai:chat")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> AiSessionOut:
    return await AIOrchestratorService(db, settings).update_session_mode(
        session_id, payload, caller
    )


@ai_router.get("/sessions/{session_id}/messages", response_model=list[AiMessageOut])
async def list_ai_session_messages(
    session_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("ai:chat")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> list[AiMessageOut]:
    return await AIOrchestratorService(db, settings).list_messages(session_id, caller)


@ai_router.post("/sessions/{session_id}/turns", response_model=AiTurnResponse)
async def execute_ai_tutor_turn(
    session_id: UUID,
    payload: AiTurnRequest,
    caller: AuthenticatedUser = Depends(require_permissions("ai:chat")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> AiTurnResponse:
    return await AIOrchestratorService(db, settings).execute_turn(session_id, payload, caller)


@ai_router.post(
    "/messages/{message_id}/flag",
    response_model=AiReviewQueueOut,
    status_code=status.HTTP_201_CREATED,
)
async def flag_ai_message(
    message_id: UUID,
    payload: AiFlagMessageRequest,
    caller: AuthenticatedUser = Depends(require_permissions("ai:chat")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> AiReviewQueueOut:
    return await AIOrchestratorService(db, settings).flag_message(message_id, payload, caller)


@ai_router.get("/knowledge/documents", response_model=list[KnowledgeDocOut])
async def list_rag_knowledge_docs(
    caller: AuthenticatedUser = Depends(require_permissions("ai:knowledge_manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[KnowledgeDocOut]:
    _ = caller
    return await list_knowledge_documents(db)


@ai_router.post(
    "/knowledge/documents",
    response_model=KnowledgeDocOut,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_rag_knowledge_doc(
    payload: KnowledgeDocIngestRequest,
    caller: AuthenticatedUser = Depends(require_permissions("ai:knowledge_manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> KnowledgeDocOut:
    return await ingest_knowledge_document(db, payload, caller)


@ai_router.post("/evals/run", response_model=AiEvalRunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_ai_eval_run(
    caller: AuthenticatedUser = Depends(require_permissions("ai:eval_manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AiEvalRunResponse:
    return await run_golden_evaluation_suite(db, caller)


@ai_router.get("/evals/runs", response_model=list[AiEvalRunResponse])
async def get_ai_eval_runs(
    caller: AuthenticatedUser = Depends(require_permissions("ai:eval_manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[AiEvalRunResponse]:
    _ = caller
    return await list_eval_runs(db)


@ai_router.get("/review-queue", response_model=list[AiReviewQueueOut])
async def get_ai_review_queue(
    caller: AuthenticatedUser = Depends(require_permissions("ai:review_queue")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> list[AiReviewQueueOut]:
    _ = caller
    return await AIOrchestratorService(db, settings).list_review_queue()


@ai_router.post("/review-queue/{item_id}/decision", response_model=AiReviewQueueOut)
async def decide_ai_review_queue_item(
    item_id: UUID,
    payload: AiReviewDecisionRequest,
    caller: AuthenticatedUser = Depends(require_permissions("ai:review_queue")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> AiReviewQueueOut:
    return await AIOrchestratorService(db, settings).decide_review_item(item_id, payload, caller)


@ai_admin_router.get("/ai-costs", response_model=AiCostSummaryResponse)
async def get_admin_ai_cost_summary(
    caller: AuthenticatedUser = Depends(require_permissions("ai:cost_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> AiCostSummaryResponse:
    _ = caller
    return await AIOrchestratorService(db, settings).get_admin_cost_summary()
