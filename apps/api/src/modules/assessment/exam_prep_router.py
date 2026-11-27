"""FastAPI router for Phase 9: Examination Preparation Ecosystem (/api/v1/exam-prep)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_current_user
from src.core.database import get_db_session
from src.modules.assessment.exam_prep_schemas import (
    AttemptDetailedSolutionsResponse,
    ExamAnalyticsResponse,
    ExamFormulaCreate,
    ExamFormulaOut,
    ExamMockGenerateRequest,
    ExamPracticeLaunchRequest,
    ExamQuestionsExplorerResponse,
    ExamRevisionPlanCreate,
    ExamRevisionPlanOut,
    ExamSyllabusChapterOut,
    ExamSyllabusChapterUpsert,
    ExamSyllabusResponse,
    ExamTrackOverviewOut,
    LaunchedExamAttemptOut,
)
from src.modules.assessment.exam_prep_service import ExamPrepService

exam_prep_router = APIRouter(prefix="/api/v1/exam-prep", tags=["exam-prep"])


@exam_prep_router.get("/tracks", response_model=list[ExamTrackOverviewOut])
async def list_exam_tracks(
    _caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ExamTrackOverviewOut]:
    """List CBSE Board, JEE Main, JEE Advanced, and NEET tracks with versioned rules & coverage audit."""
    return await ExamPrepService(db).list_exam_tracks_overview()


@exam_prep_router.get("/{exam_code}/syllabus", response_model=ExamSyllabusResponse)
async def get_exam_syllabus(
    exam_code: str,
    _caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    pattern_version_label: str | None = Query(default=None),
) -> ExamSyllabusResponse:
    """Return versioned syllabus & chapter mappings with honest coverage audit metrics."""
    return await ExamPrepService(db).get_exam_syllabus(
        exam_code=exam_code,
        pattern_version_label=pattern_version_label,
    )


@exam_prep_router.post(
    "/{exam_code}/syllabus",
    response_model=ExamSyllabusChapterOut,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_exam_syllabus_chapter(
    exam_code: str,
    payload: ExamSyllabusChapterUpsert,
    caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExamSyllabusChapterOut:
    """Create or update a versioned syllabus chapter mapping (content/academic reviewer/admin only)."""
    return await ExamPrepService(db).upsert_syllabus_chapter(
        exam_code=exam_code,
        payload=payload,
        caller=caller,
    )


@exam_prep_router.get("/{exam_code}/questions", response_model=ExamQuestionsExplorerResponse)
async def explore_exam_questions(
    exam_code: str,
    _caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    verified_pyq_only: bool = Query(default=False),
    exam_year: int | None = Query(default=None, ge=1980, le=2035),
    exam_session: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    question_type: str | None = Query(default=None),
    subject_id: UUID | None = Query(default=None),
    chapter_id: UUID | None = Query(default=None),
    topic_id: UUID | None = Query(default=None),
    concept_id: UUID | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
) -> ExamQuestionsExplorerResponse:
    """Explore answer-redacted exam questions & strictly verified PYQs with year/session/difficulty/type filters."""
    return await ExamPrepService(db).explore_exam_questions(
        exam_code=exam_code,
        verified_pyq_only=verified_pyq_only,
        exam_year=exam_year,
        exam_session=exam_session,
        difficulty=difficulty,
        question_type=question_type,
        subject_id=subject_id,
        chapter_id=chapter_id,
        topic_id=topic_id,
        concept_id=concept_id,
        limit=limit,
    )


@exam_prep_router.post(
    "/{exam_code}/practice",
    response_model=LaunchedExamAttemptOut,
    status_code=status.HTTP_201_CREATED,
)
async def launch_exam_practice(
    exam_code: str,
    payload: ExamPracticeLaunchRequest,
    caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> LaunchedExamAttemptOut:
    """Launch a chapter-wise, topic-wise, or verified-PYQ exam practice attempt."""
    return await ExamPrepService(db).launch_exam_practice(
        exam_code=exam_code,
        payload=payload,
        caller=caller,
    )


@exam_prep_router.post(
    "/{exam_code}/mocks/generate",
    response_model=LaunchedExamAttemptOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_and_start_mock(
    exam_code: str,
    payload: ExamMockGenerateRequest,
    caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> LaunchedExamAttemptOut:
    """Generate and start a server-authoritative timed full/section mock from a versioned ExamPattern."""
    return await ExamPrepService(db).generate_and_start_mock_test(
        exam_code=exam_code,
        payload=payload,
        caller=caller,
    )


@exam_prep_router.get("/{exam_code}/analytics", response_model=ExamAnalyticsResponse)
async def get_exam_analytics(
    exam_code: str,
    caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExamAnalyticsResponse:
    """Return student exam accuracy, speed/pacing, weak subjects/chapters/concepts, history, and recommendations."""
    return await ExamPrepService(db).get_student_exam_analytics(
        exam_code=exam_code,
        student_id=caller.id,
    )


@exam_prep_router.get("/{exam_code}/formulas", response_model=list[ExamFormulaOut])
async def list_exam_formulas(
    exam_code: str,
    _caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    subject_id: UUID | None = Query(default=None),
    chapter_id: UUID | None = Query(default=None),
    high_yield_only: bool = Query(default=False),
) -> list[ExamFormulaOut]:
    """List published formula revision sheets for an exam track."""
    return await ExamPrepService(db).list_formula_sheets(
        exam_code=exam_code,
        subject_id=subject_id,
        chapter_id=chapter_id,
        high_yield_only=high_yield_only,
    )


@exam_prep_router.post(
    "/{exam_code}/formulas",
    response_model=ExamFormulaOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_exam_formula(
    exam_code: str,
    payload: ExamFormulaCreate,
    caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExamFormulaOut:
    """Author a formula revision card (content/academic reviewer/admin only)."""
    return await ExamPrepService(db).create_formula_sheet(
        exam_code=exam_code,
        payload=payload,
        caller=caller,
    )


@exam_prep_router.get("/{exam_code}/revision-plans", response_model=list[ExamRevisionPlanOut])
async def list_exam_revision_plans(
    exam_code: str,
    caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ExamRevisionPlanOut]:
    """List saved exam revision plans for the authenticated student."""
    return await ExamPrepService(db).list_revision_plans(
        exam_code=exam_code,
        student_id=caller.id,
    )


@exam_prep_router.post(
    "/{exam_code}/revision-plans",
    response_model=ExamRevisionPlanOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_exam_revision_plan(
    exam_code: str,
    payload: ExamRevisionPlanCreate,
    caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExamRevisionPlanOut:
    """Generate and persist a personalized exam revision plan prioritizing weak high-yield chapters."""
    return await ExamPrepService(db).create_revision_plan(
        exam_code=exam_code,
        payload=payload,
        caller=caller,
    )


@exam_prep_router.get(
    "/attempts/{attempt_id}/solutions",
    response_model=AttemptDetailedSolutionsResponse,
)
async def get_attempt_detailed_solutions(
    attempt_id: UUID,
    caller: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AttemptDetailedSolutionsResponse:
    """Return detailed post-attempt solutions (strictly returns 403 while attempt is in_progress)."""
    return await ExamPrepService(db).get_attempt_detailed_solutions(
        attempt_id=attempt_id,
        caller=caller,
    )
