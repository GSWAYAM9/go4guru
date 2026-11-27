"""Public contract boundary for revision module (Phase 5 Flashcards, SM-2+ & Planner)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.revision.models import StudentFlashcard, StudyPlan, StudyPlanItem
from src.modules.revision.router import revision_router

MODULE_NAME = "revision"
MODULE_PHASE = "Phase 5"
MODULE_STATUS = "IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class StudentRevisionSummaryContract:
    """Privacy-safe revision & study-plan summary for Parent/Mentor dashboards."""

    total_flashcards: int
    due_flashcards: int
    active_study_plans: int
    completed_plan_items: int
    total_plan_items: int


async def get_student_revision_summary(
    db: AsyncSession, student_id: UUID
) -> StudentRevisionSummaryContract:
    """Compute real revision counts strictly for student_id."""
    now = datetime.now(UTC)
    total_cards = int(
        await db.scalar(
            select(func.count(StudentFlashcard.id)).where(
                StudentFlashcard.student_id == student_id
            )
        )
        or 0
    )
    due_cards = int(
        await db.scalar(
            select(func.count(StudentFlashcard.id)).where(
                StudentFlashcard.student_id == student_id,
                StudentFlashcard.due_at <= now,
            )
        )
        or 0
    )
    plan_ids = list(
        (
            await db.scalars(
                select(StudyPlan.id).where(
                    StudyPlan.student_id == student_id, StudyPlan.status == "active"
                )
            )
        ).all()
    )
    total_items = 0
    done_items = 0
    if plan_ids:
        total_items = int(
            await db.scalar(
                select(func.count(StudyPlanItem.id)).where(StudyPlanItem.study_plan_id.in_(plan_ids))
            )
            or 0
        )
        done_items = int(
            await db.scalar(
                select(func.count(StudyPlanItem.id)).where(
                    StudyPlanItem.study_plan_id.in_(plan_ids),
                    StudyPlanItem.status == "completed",
                )
            )
            or 0
        )
    return StudentRevisionSummaryContract(
        total_flashcards=total_cards,
        due_flashcards=due_cards,
        active_study_plans=len(plan_ids),
        completed_plan_items=done_items,
        total_plan_items=total_items,
    )


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "StudentRevisionSummaryContract",
    "get_student_revision_summary",
    "revision_router",
]
