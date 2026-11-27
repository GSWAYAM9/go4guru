"""Public contract boundary for assessment module (Phase 1 practice engine subset)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.assessment.exam_prep_router import exam_prep_router
from src.modules.assessment.exam_router import assessments_router, quizzes_router
from src.modules.assessment.models import (
    AssessmentAttempt,
    AttemptAnswer,
    PracticeSession,
    QuestionAttempt,
    SavedQuestion,
    StudentNote,
)
from src.modules.assessment.service_and_router import (
    bookmarks_router,
    notes_router,
    practice_router,
)

MODULE_NAME = "assessment"
MODULE_PHASE = "Phase 1 (Practice) + Phase 2 (Quizzes & Assessments) + Phase 9 (Exam Prep Ecosystem)"
MODULE_STATUS = "IMPLEMENTED_PHASE_9"


@dataclass(frozen=True, slots=True)
class RecentAttemptContract:
    attempt_id: UUID
    question_id: UUID
    is_correct: bool
    score_awarded: float
    hints_used_count: int
    attempted_at: datetime


@dataclass(frozen=True, slots=True)
class StudentProgressContract:
    total_attempts: int
    correct_attempts: int
    total_sessions: int
    hints_used_total: int
    saved_questions_count: int
    notes_count: int
    recent_attempts: tuple[RecentAttemptContract, ...]
    session_subject_ids: tuple[UUID | None, ...]


async def get_student_progress_snapshot(
    db: AsyncSession, student_id: UUID
) -> StudentProgressContract:
    """Compute real database progress metrics strictly for student_id."""
    total_attempts = int(
        await db.scalar(
            select(func.count(QuestionAttempt.id)).where(QuestionAttempt.student_id == student_id)
        )
        or 0
    )
    correct_attempts = int(
        await db.scalar(
            select(func.count(QuestionAttempt.id)).where(
                QuestionAttempt.student_id == student_id,
                QuestionAttempt.is_correct.is_(True),
            )
        )
        or 0
    )
    hints_used_total = int(
        await db.scalar(
            select(func.coalesce(func.sum(QuestionAttempt.hints_used_count), 0)).where(
                QuestionAttempt.student_id == student_id
            )
        )
        or 0
    )
    total_sessions = int(
        await db.scalar(
            select(func.count(PracticeSession.id)).where(PracticeSession.student_id == student_id)
        )
        or 0
    )
    saved_count = int(
        await db.scalar(
            select(func.count(SavedQuestion.question_id)).where(
                SavedQuestion.student_id == student_id
            )
        )
        or 0
    )
    notes_count = int(
        await db.scalar(
            select(func.count(StudentNote.id)).where(StudentNote.student_id == student_id)
        )
        or 0
    )

    recent_rows = (
        await db.scalars(
            select(QuestionAttempt)
            .where(QuestionAttempt.student_id == student_id)
            .order_by(QuestionAttempt.attempted_at.desc())
            .limit(10)
        )
    ).all()
    subj_rows = (
        await db.scalars(
            select(PracticeSession.subject_id).where(PracticeSession.student_id == student_id)
        )
    ).all()

    return StudentProgressContract(
        total_attempts=total_attempts,
        correct_attempts=correct_attempts,
        total_sessions=total_sessions,
        hints_used_total=hints_used_total,
        saved_questions_count=saved_count,
        notes_count=notes_count,
        recent_attempts=tuple(
            RecentAttemptContract(
                attempt_id=r.id,
                question_id=r.question_id,
                is_correct=r.is_correct,
                score_awarded=float(r.score_awarded),
                hints_used_count=r.hints_used_count,
                attempted_at=r.attempted_at,
            )
            for r in recent_rows
        ),
        session_subject_ids=tuple(subj_rows),
    )


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "AttemptEvidenceContract",
    "CohortAssessmentMetrics",
    "StudentProgressContract",
    "assessments_router",
    "bookmarks_router",
    "exam_prep_router",
    "get_cohort_assessment_metrics",
    "get_student_attempt_evidence",
    "get_student_progress_snapshot",
    "notes_router",
    "practice_router",
    "quizzes_router",
]


@dataclass(frozen=True, slots=True)
class AttemptEvidenceContract:
    """Unified normalized practice + assessment attempt evidence for adaptive mastery."""

    attempt_id: UUID
    question_id: UUID | None
    question_version_id: UUID
    is_correct: bool
    hints_used_count: int
    time_spent_seconds: int
    attempted_at: datetime
    source_context: str


async def get_student_attempt_evidence(
    db: AsyncSession, student_id: UUID
) -> list[AttemptEvidenceContract]:
    """Collect chronological student question attempt signals across practice & assessments."""
    evidence: list[AttemptEvidenceContract] = []

    practice_rows = (
        await db.scalars(
            select(QuestionAttempt)
            .where(QuestionAttempt.student_id == student_id)
            .order_by(QuestionAttempt.attempted_at.asc())
        )
    ).all()
    for p in practice_rows:
        evidence.append(
            AttemptEvidenceContract(
                attempt_id=p.id,
                question_id=p.question_id,
                question_version_id=p.question_version_id,
                is_correct=bool(p.is_correct),
                hints_used_count=int(p.hints_used_count),
                time_spent_seconds=int(p.time_spent_seconds),
                attempted_at=p.attempted_at,
                source_context="practice",
            )
        )

    exam_rows = (
        await db.execute(
            select(AttemptAnswer, AssessmentAttempt)
            .join(AssessmentAttempt, AttemptAnswer.attempt_id == AssessmentAttempt.id)
            .where(
                AssessmentAttempt.student_id == student_id,
                AssessmentAttempt.status.in_(["submitted", "auto_submitted", "graded"]),
                AttemptAnswer.is_correct.is_not(None),
            )
        )
    ).all()
    for ans, att in exam_rows:
        evidence.append(
            AttemptEvidenceContract(
                attempt_id=ans.id,
                question_id=None,
                question_version_id=ans.question_version_id,
                is_correct=bool(ans.is_correct),
                hints_used_count=0,
                time_spent_seconds=int(ans.time_spent_seconds),
                attempted_at=att.submitted_at or ans.last_saved_at,
                source_context="assessment",
            )
        )

    evidence.sort(key=lambda item: item.attempted_at)
    return evidence


@dataclass(frozen=True, slots=True)
class CohortAssessmentMetrics:
    total_submitted_attempts: int
    average_accuracy_pct: float


async def get_cohort_assessment_metrics(db: AsyncSession) -> CohortAssessmentMetrics:
    """Return anonymized aggregate cohort assessment stats (zero student PII)."""
    rows = (
        await db.scalars(
            select(AssessmentAttempt).where(
                AssessmentAttempt.status.in_(["submitted", "auto_submitted", "graded"])
            )
        )
    ).all()
    if not rows:
        return CohortAssessmentMetrics(total_submitted_attempts=0, average_accuracy_pct=0.0)
    avg_acc = round(sum(float(r.accuracy_pct or 0.0) for r in rows) / len(rows), 2)
    return CohortAssessmentMetrics(
        total_submitted_attempts=len(rows),
        average_accuracy_pct=avg_acc,
    )
