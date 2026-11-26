"""Public contract boundary for learning module (Phase 1 Dashboard + Phase 5 Adaptive)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.learning.adaptive_router import learning_router
from src.modules.learning.models import StudentConceptMastery
from src.modules.learning.router import dashboard_router

MODULE_NAME = "learning"
MODULE_PHASE = "Phase 1 (Dashboard) + Phase 5 (Adaptive Concept Mastery)"
MODULE_STATUS = "IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class WeakConceptSummaryContract:
    concept_id: UUID
    mastery_score: float
    band: str


async def get_concept_mastery_scores_map(db: AsyncSession, student_id: UUID) -> dict[UUID, float]:
    """Return latest concept mastery scores (0..100) keyed by concept_id."""
    rows = (
        await db.scalars(
            select(StudentConceptMastery).where(StudentConceptMastery.student_id == student_id)
        )
    ).all()
    return {row.concept_id: float(row.mastery_score) for row in rows}


async def list_weak_concept_summaries(
    db: AsyncSession, student_id: UUID, *, threshold: float = 60.0
) -> list[WeakConceptSummaryContract]:
    rows = (
        await db.scalars(
            select(StudentConceptMastery)
            .where(
                StudentConceptMastery.student_id == student_id,
                StudentConceptMastery.mastery_score < threshold,
            )
            .order_by(StudentConceptMastery.mastery_score.asc())
        )
    ).all()
    return [
        WeakConceptSummaryContract(
            concept_id=r.concept_id,
            mastery_score=float(r.mastery_score),
            band=r.band,
        )
        for r in rows
    ]


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "WeakConceptSummaryContract",
    "dashboard_router",
    "get_concept_mastery_scores_map",
    "learning_router",
    "list_weak_concept_summaries",
]
