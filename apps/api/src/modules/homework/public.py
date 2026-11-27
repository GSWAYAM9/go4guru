"""Public contract boundary for Phase 6 Homework AI module (F-029)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.homework.models import HomeworkSubmission
from src.modules.homework.router import homework_router

MODULE_NAME = "homework"
MODULE_PHASE = "Phase 6"
MODULE_STATUS = "IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class HomeworkProgressSummaryContract:
    """Aggregate homework metrics (never exposes raw AI coaching transcripts to parents)."""

    total_submissions: int
    completed_submissions: int
    total_retries: int


async def get_student_homework_summary(
    db: AsyncSession, student_id: UUID
) -> HomeworkProgressSummaryContract:
    """Return aggregate homework counts for authorized educator/parent summary cards."""
    total = int(
        await db.scalar(
            select(func.count(HomeworkSubmission.id)).where(
                HomeworkSubmission.student_id == student_id
            )
        )
        or 0
    )
    completed = int(
        await db.scalar(
            select(func.count(HomeworkSubmission.id)).where(
                HomeworkSubmission.student_id == student_id,
                HomeworkSubmission.status == "completed",
            )
        )
        or 0
    )
    retries = int(
        await db.scalar(
            select(func.coalesce(func.sum(HomeworkSubmission.retry_count), 0)).where(
                HomeworkSubmission.student_id == student_id
            )
        )
        or 0
    )
    return HomeworkProgressSummaryContract(
        total_submissions=total,
        completed_submissions=completed,
        total_retries=retries,
    )


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "HomeworkProgressSummaryContract",
    "get_student_homework_summary",
    "homework_router",
]
