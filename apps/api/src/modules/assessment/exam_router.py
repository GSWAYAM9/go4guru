"""HTTP API routers for Configurable Quiz Engine & Server-Authoritative Assessments."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.modules.assessment.exam_schemas import (
    AttemptHistoryItem,
    AttemptResultResponse,
    AttemptStateResponse,
    AutosaveAnswersRequest,
    AutosaveResponse,
    ExamPatternCreate,
    ExamPatternOut,
    QuizGenerateRequest,
    QuizOut,
    SubmitAttemptRequest,
    TestCreateRequest,
    TestOut,
)
from src.modules.assessment.exam_service import ExamAssessmentService

quizzes_router = APIRouter(prefix="/api/v1/quizzes", tags=["quizzes"])
assessments_router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])


@quizzes_router.post("/generate", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    payload: QuizGenerateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("quiz:create")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> QuizOut:
    return await ExamAssessmentService(db).generate_quiz(payload, caller)


@quizzes_router.get("", response_model=list[QuizOut])
async def list_quizzes(
    caller: AuthenticatedUser = Depends(require_permissions("quiz:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[QuizOut]:
    return await ExamAssessmentService(db).list_quizzes(caller)


@quizzes_router.post(
    "/{quiz_id}/start",
    response_model=AttemptStateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_quiz_attempt(
    quiz_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("quiz:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AttemptStateResponse:
    return await ExamAssessmentService(db).start_quiz_attempt(quiz_id, caller)


@assessments_router.get("/exam-patterns", response_model=list[ExamPatternOut])
async def list_exam_patterns(
    caller: AuthenticatedUser = Depends(require_permissions("assessment:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[ExamPatternOut]:
    return await ExamAssessmentService(db).list_exam_patterns()


@assessments_router.post(
    "/exam-patterns", response_model=ExamPatternOut, status_code=status.HTTP_201_CREATED
)
async def create_exam_pattern(
    payload: ExamPatternCreate,
    caller: AuthenticatedUser = Depends(require_permissions("exam_pattern:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ExamPatternOut:
    return await ExamAssessmentService(db).create_exam_pattern(payload, caller)


@assessments_router.get("/tests", response_model=list[TestOut])
async def list_tests(
    caller: AuthenticatedUser = Depends(require_permissions("assessment:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[TestOut]:
    return await ExamAssessmentService(db).list_tests(caller)


@assessments_router.post("/tests", response_model=TestOut, status_code=status.HTTP_201_CREATED)
async def create_test(
    payload: TestCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("assessment:create")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> TestOut:
    return await ExamAssessmentService(db).create_test(payload, caller)


@assessments_router.post("/tests/{test_id}/publish", response_model=TestOut)
async def publish_test(
    test_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("assessment:create")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> TestOut:
    return await ExamAssessmentService(db).publish_test(test_id, caller)


@assessments_router.post(
    "/tests/{test_id}/attempts",
    response_model=AttemptStateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_test_attempt(
    test_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("assessment:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AttemptStateResponse:
    return await ExamAssessmentService(db).start_test_attempt(test_id, caller)


@assessments_router.get("/attempts", response_model=list[AttemptHistoryItem])
async def list_attempt_history(
    caller: AuthenticatedUser = Depends(require_permissions("assessment:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[AttemptHistoryItem]:
    return await ExamAssessmentService(db).list_attempt_history(caller)


@assessments_router.get("/attempts/{attempt_id}/state", response_model=AttemptStateResponse)
async def get_attempt_state(
    attempt_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("assessment:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AttemptStateResponse:
    return await ExamAssessmentService(db).get_attempt_state(attempt_id, caller)


@assessments_router.put("/attempts/{attempt_id}/answers", response_model=AutosaveResponse)
async def autosave_attempt_answers(
    attempt_id: UUID,
    payload: AutosaveAnswersRequest,
    caller: AuthenticatedUser = Depends(require_permissions("assessment:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AutosaveResponse:
    return await ExamAssessmentService(db).autosave_answers(attempt_id, payload, caller)


@assessments_router.post("/attempts/{attempt_id}/submit", response_model=AttemptResultResponse)
async def submit_attempt(
    attempt_id: UUID,
    payload: SubmitAttemptRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    caller: AuthenticatedUser = Depends(require_permissions("assessment:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AttemptResultResponse:
    return await ExamAssessmentService(db).submit_attempt(
        attempt_id,
        payload or SubmitAttemptRequest(),
        caller,
        idempotency_key=idempotency_key,
    )


@assessments_router.get("/attempts/{attempt_id}/result", response_model=AttemptResultResponse)
async def get_attempt_result(
    attempt_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("assessment:attempt")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AttemptResultResponse:
    return await ExamAssessmentService(db).get_attempt_result(attempt_id, caller)
