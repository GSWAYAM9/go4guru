"""FastAPI HTTP router for Phase 5 Adaptive Concept Mastery & Learning Paths."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.core.errors import AppError
from src.modules.learning.schemas import (
    AdaptiveOverviewOut,
    ConceptMasteryOut,
    LearningPathCreateRequest,
    LearningPathItemOut,
    LearningPathItemStatusRequest,
    LearningPathOut,
    MisconceptionCreateRequest,
    MisconceptionOut,
    RecommendationItemOut,
)
from src.modules.learning.service import AdaptiveLearningService

learning_router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


@learning_router.post("/recompute", response_model=AdaptiveOverviewOut)
async def recompute_learning_mastery(
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AdaptiveOverviewOut:
    return await AdaptiveLearningService(db).get_adaptive_overview(caller)


@learning_router.get("/overview", response_model=AdaptiveOverviewOut)
async def get_learning_adaptive_overview(
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AdaptiveOverviewOut:
    return await AdaptiveLearningService(db).get_adaptive_overview(caller)


@learning_router.get("/mastery", response_model=list[ConceptMasteryOut])
async def list_concept_mastery(
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[ConceptMasteryOut]:
    mastery, _, _ = await AdaptiveLearningService(db).recompute_student_mastery(caller)
    return mastery


@learning_router.get("/mastery/{concept_id}", response_model=ConceptMasteryOut)
async def get_concept_mastery_detail(
    concept_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ConceptMasteryOut:
    mastery, _, _ = await AdaptiveLearningService(db).recompute_student_mastery(caller)
    for item in mastery:
        if item.concept_id == concept_id:
            return item
    raise AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        code="CONCEPT_MASTERY_NOT_FOUND",
        message="No mastery record found for that concept yet.",
    )


@learning_router.get("/weak-concepts", response_model=list[ConceptMasteryOut])
async def list_weak_concepts(
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[ConceptMasteryOut]:
    overview = await AdaptiveLearningService(db).get_adaptive_overview(caller)
    return overview.weak_concepts


@learning_router.get("/recommendations", response_model=list[RecommendationItemOut])
async def list_adaptive_recommendations(
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[RecommendationItemOut]:
    _, recs, _ = await AdaptiveLearningService(db).recompute_student_mastery(caller)
    return recs


@learning_router.get("/misconceptions", response_model=list[MisconceptionOut])
async def list_misconceptions(
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[MisconceptionOut]:
    return await AdaptiveLearningService(db).list_misconceptions(caller)


@learning_router.post(
    "/misconceptions",
    response_model=MisconceptionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_misconception(
    payload: MisconceptionCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> MisconceptionOut:
    return await AdaptiveLearningService(db).record_misconception(payload, caller)


@learning_router.post("/misconceptions/{misconception_id}/resolve", response_model=MisconceptionOut)
async def resolve_misconception(
    misconception_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> MisconceptionOut:
    return await AdaptiveLearningService(db).resolve_misconception(misconception_id, caller)


@learning_router.post(
    "/learning-paths", response_model=LearningPathOut, status_code=status.HTTP_201_CREATED
)
async def generate_learning_path(
    payload: LearningPathCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> LearningPathOut:
    return await AdaptiveLearningService(db).generate_learning_path(payload, caller)


@learning_router.get("/learning-paths", response_model=list[LearningPathOut])
async def get_learning_paths(
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[LearningPathOut]:
    return await AdaptiveLearningService(db).list_learning_paths(caller)


@learning_router.patch("/learning-paths/items/{item_id}", response_model=LearningPathItemOut)
async def update_learning_path_item(
    item_id: UUID,
    payload: LearningPathItemStatusRequest,
    caller: AuthenticatedUser = Depends(require_permissions("learning:adaptive_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> LearningPathItemOut:
    return await AdaptiveLearningService(db).update_path_item_status(item_id, payload, caller)
