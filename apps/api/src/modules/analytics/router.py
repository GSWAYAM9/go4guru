"""HTTP routes for Learning Analytics (`F-034`)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.modules.analytics.models import AnalyticsSnapshot, LearningEvent
from src.modules.analytics.service import process_outbox_learning_events
from src.modules.assessment.public import get_cohort_assessment_metrics

analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class LearningEventOut(BaseModel):
    id: UUID
    event_type: str
    concept_id: UUID | None
    entity_id: UUID | None
    metrics_jsonb: dict[str, Any]
    occurred_at: datetime


class StudentAnalyticsOverviewResponse(BaseModel):
    assessments_completed: int
    average_assessment_accuracy_pct: float
    practice_attempts: int
    practice_correct: int
    practice_accuracy_pct: float
    total_learning_events: int
    recent_events: list[LearningEventOut]


class CohortAnalyticsResponse(BaseModel):
    total_submitted_attempts: int
    average_accuracy_pct: float


@analytics_router.get("/student/overview", response_model=StudentAnalyticsOverviewResponse)
async def get_student_analytics_overview(
    caller: AuthenticatedUser = Depends(require_permissions("analytics:read_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> StudentAnalyticsOverviewResponse:
    # Ensure any freshly committed outbox events are projected idempotently before reading snapshot
    await process_outbox_learning_events(db, limit=100)

    snap = await db.scalar(
        select(AnalyticsSnapshot).where(
            AnalyticsSnapshot.student_id == caller.id,
            AnalyticsSnapshot.scope_type == "student_overview",
            AnalyticsSnapshot.scope_key == "all",
        )
    )
    events = list(
        (
            await db.scalars(
                select(LearningEvent)
                .where(LearningEvent.student_id == caller.id)
                .order_by(LearningEvent.occurred_at.desc())
                .limit(20)
            )
        ).all()
    )

    m = snap.metrics_jsonb if snap else {}
    return StudentAnalyticsOverviewResponse(
        assessments_completed=int(m.get("assessments_completed", 0)),
        average_assessment_accuracy_pct=float(m.get("average_assessment_accuracy_pct", 0.0)),
        practice_attempts=int(m.get("practice_attempts", 0)),
        practice_correct=int(m.get("practice_correct", 0)),
        practice_accuracy_pct=float(m.get("practice_accuracy_pct", 0.0)),
        total_learning_events=int(m.get("total_learning_events", 0)),
        recent_events=[
            LearningEventOut(
                id=e.id,
                event_type=e.event_type,
                concept_id=e.concept_id,
                entity_id=e.entity_id,
                metrics_jsonb=e.metrics_jsonb,
                occurred_at=e.occurred_at,
            )
            for e in events
        ],
    )


@analytics_router.get("/cohort", response_model=CohortAnalyticsResponse)
async def get_cohort_analytics(
    caller: AuthenticatedUser = Depends(require_permissions("analytics:read_cohort")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> CohortAnalyticsResponse:
    metrics = await get_cohort_assessment_metrics(db)
    return CohortAnalyticsResponse(
        total_submitted_attempts=metrics.total_submitted_attempts,
        average_accuracy_pct=metrics.average_accuracy_pct,
    )
