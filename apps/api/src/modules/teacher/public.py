"""Public contract boundary for teacher module (Phase 7 F-031)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.teacher.models import ClassEnrollment, TeacherAssignment
from src.modules.teacher.router import teacher_router

MODULE_NAME = "teacher"
MODULE_PHASE = "Phase 7"
MODULE_STATUS = "IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class UpcomingAssignmentContract:
    assignment_id: UUID
    title: str
    assignment_type: str
    due_at: datetime | None
    max_marks: float


async def list_upcoming_assignments_for_student(
    db: AsyncSession, student_id: UUID
) -> list[UpcomingAssignmentContract]:
    """Return published assignments/quizzes/tests for classes the student is actively enrolled in."""
    class_ids = list(
        (
            await db.scalars(
                select(ClassEnrollment.class_id).where(
                    ClassEnrollment.student_id == student_id,
                    ClassEnrollment.status == "active",
                )
            )
        ).all()
    )
    if not class_ids:
        return []
    rows = (
        await db.scalars(
            select(TeacherAssignment)
            .where(
                TeacherAssignment.class_id.in_(class_ids),
                TeacherAssignment.status == "published",
            )
            .order_by(TeacherAssignment.due_at.asc().nullslast())
            .limit(15)
        )
    ).all()
    return [
        UpcomingAssignmentContract(
            assignment_id=r.id,
            title=r.title,
            assignment_type=r.assignment_type,
            due_at=r.due_at,
            max_marks=float(r.max_marks),
        )
        for r in rows
    ]


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "UpcomingAssignmentContract",
    "list_upcoming_assignments_for_student",
    "teacher_router",
]
