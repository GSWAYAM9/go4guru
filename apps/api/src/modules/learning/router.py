"""Student Core Dashboard & Progress Tracking router (Phase 1 `F-030`)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.modules.assessment.public import get_student_progress_snapshot
from src.modules.curriculum.public import get_chapter_and_subject_labels
from src.modules.identity.public import get_student_onboarding_summary

dashboard_router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


class SubjectActivityItem(BaseModel):
    subject_id: UUID | None
    subject_name: str
    practice_sessions_count: int


class RecentAttemptItem(BaseModel):
    attempt_id: UUID
    question_id: UUID
    is_correct: bool
    score_awarded: float
    hints_used_count: int
    attempted_at: datetime


class StudentDashboardResponse(BaseModel):
    """Real database-backed student workspace summary (zero fake streaks/metrics)."""

    onboarding_completed: bool
    primary_exam_target: str
    daily_study_minutes_target: int
    total_attempts: int
    correct_attempts: int
    accuracy_pct: float
    total_practice_sessions: int
    hints_used_total: int
    saved_questions_count: int
    notes_count: int
    subject_activity: list[SubjectActivityItem]
    recent_attempts: list[RecentAttemptItem]
    unimplemented_features_note: str


@dashboard_router.get("/student", response_model=StudentDashboardResponse)
async def get_student_dashboard(
    caller: AuthenticatedUser = Depends(require_permissions("dashboard:student_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> StudentDashboardResponse:
    onboarding = await get_student_onboarding_summary(db, caller.id)
    progress = await get_student_progress_snapshot(db, caller.id)
    _, subjects_by_id = await get_chapter_and_subject_labels(db)

    counts_by_subject: dict[UUID | None, int] = {}
    for sid in progress.session_subject_ids:
        counts_by_subject[sid] = counts_by_subject.get(sid, 0) + 1

    accuracy = (
        round((progress.correct_attempts / progress.total_attempts) * 100.0, 2)
        if progress.total_attempts > 0
        else 0.0
    )

    return StudentDashboardResponse(
        onboarding_completed=onboarding.onboarding_completed,
        primary_exam_target=onboarding.primary_exam_target,
        daily_study_minutes_target=onboarding.daily_study_minutes_target,
        total_attempts=progress.total_attempts,
        correct_attempts=progress.correct_attempts,
        accuracy_pct=accuracy,
        total_practice_sessions=progress.total_sessions,
        hints_used_total=progress.hints_used_total,
        saved_questions_count=progress.saved_questions_count,
        notes_count=progress.notes_count,
        subject_activity=[
            SubjectActivityItem(
                subject_id=sid,
                subject_name=subjects_by_id.get(sid, "General Practice")
                if sid
                else "General Practice",
                practice_sessions_count=cnt,
            )
            for sid, cnt in counts_by_subject.items()
        ],
        recent_attempts=[
            RecentAttemptItem(
                attempt_id=a.attempt_id,
                question_id=a.question_id,
                is_correct=a.is_correct,
                score_awarded=a.score_awarded,
                hints_used_count=a.hints_used_count,
                attempted_at=a.attempted_at,
            )
            for a in progress.recent_attempts
        ],
        unimplemented_features_note=(
            "Quizzes/Exams activate in Phase 2, AI Tutor in Phase 3, "
            "Live Classroom in Phase 4, and Spaced Repetition in Phase 5."
        ),
    )
