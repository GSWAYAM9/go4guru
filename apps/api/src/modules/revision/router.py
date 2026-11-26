"""FastAPI HTTP routes for Phase 5 Flashcards, SM-2+ Reviews, Study Plans & Analytics."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.modules.revision.schemas import (
    FlashcardCreateRequest,
    FlashcardOut,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
    RevisionAnalyticsOut,
    StudyPlanCreateRequest,
    StudyPlanItemOut,
    StudyPlanItemStatusRequest,
    StudyPlanOut,
    SyncMissedResponse,
)
from src.modules.revision.service import RevisionService

revision_router = APIRouter(prefix="/api/v1/revision", tags=["revision"])


@revision_router.get("/flashcards", response_model=list[FlashcardOut])
async def list_flashcards(
    card_type: str | None = Query(default=None),
    caller: AuthenticatedUser = Depends(require_permissions("revision:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[FlashcardOut]:
    return await RevisionService(db).list_flashcards(caller, card_type=card_type)


@revision_router.post(
    "/flashcards", response_model=FlashcardOut, status_code=status.HTTP_201_CREATED
)
async def create_flashcard(
    payload: FlashcardCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("revision:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> FlashcardOut:
    return await RevisionService(db).create_flashcard(payload, caller)


@revision_router.post("/flashcards/sync-missed", response_model=SyncMissedResponse)
async def sync_missed_question_flashcards(
    caller: AuthenticatedUser = Depends(require_permissions("revision:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> SyncMissedResponse:
    return await RevisionService(db).sync_missed_questions(caller)


@revision_router.get("/flashcards/due", response_model=list[FlashcardOut])
async def get_due_flashcards(
    caller: AuthenticatedUser = Depends(require_permissions("revision:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[FlashcardOut]:
    return await RevisionService(db).list_flashcards(caller, due_only=True)


@revision_router.post("/flashcards/{flashcard_id}/review", response_model=FlashcardReviewResponse)
async def submit_flashcard_review(
    flashcard_id: UUID,
    payload: FlashcardReviewRequest,
    caller: AuthenticatedUser = Depends(require_permissions("revision:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> FlashcardReviewResponse:
    return await RevisionService(db).review_flashcard(flashcard_id, payload, caller)


@revision_router.get("/study-plans", response_model=list[StudyPlanOut])
async def list_study_plans(
    caller: AuthenticatedUser = Depends(require_permissions("revision:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[StudyPlanOut]:
    return await RevisionService(db).list_study_plans(caller)


@revision_router.post(
    "/study-plans", response_model=StudyPlanOut, status_code=status.HTTP_201_CREATED
)
async def create_study_plan(
    payload: StudyPlanCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("revision:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> StudyPlanOut:
    return await RevisionService(db).generate_study_plan(payload, caller)


@revision_router.patch("/study-plans/items/{item_id}", response_model=StudyPlanItemOut)
async def update_study_plan_item(
    item_id: UUID,
    payload: StudyPlanItemStatusRequest,
    caller: AuthenticatedUser = Depends(require_permissions("revision:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> StudyPlanItemOut:
    return await RevisionService(db).update_study_plan_item_status(item_id, payload, caller)


@revision_router.get("/analytics", response_model=RevisionAnalyticsOut)
async def get_revision_analytics(
    caller: AuthenticatedUser = Depends(require_permissions("revision:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> RevisionAnalyticsOut:
    return await RevisionService(db).get_revision_analytics(caller)
