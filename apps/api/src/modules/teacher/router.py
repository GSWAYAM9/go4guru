"""FastAPI router for Teacher Ecosystem (/api/v1/teacher/*)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import (
    AuthenticatedUser,
    get_db_session,
    require_permissions,
    require_roles,
)
from src.modules.teacher.schemas import (
    AssignmentSubmissionResponse,
    ClassEnrollmentResponse,
    ClassEnrollStudentRequest,
    QuestionBankOptionItem,
    StudentAssignmentSubmitRequest,
    TeacherAssignmentCreateRequest,
    TeacherAssignmentResponse,
    TeacherClassAnalyticsResponse,
    TeacherClassCreateRequest,
    TeacherClassResponse,
    TeacherDashboardResponse,
    TeacherOverrideGradeRequest,
    TeacherSectionCreateRequest,
    TeacherSectionResponse,
    TeacherStudentAnalyticsResponse,
)
from src.modules.teacher.service import (
    create_assignment,
    create_section,
    create_teacher_class,
    enroll_student_in_class,
    export_class_report_csv,
    get_class_analytics,
    get_student_analytics_for_teacher,
    get_teacher_dashboard,
    list_assignment_submissions,
    list_assignments,
    list_class_students,
    list_question_bank_options,
    list_sections,
    override_submission_grade,
    run_ai_assisted_grade,
    submit_assignment_as_student,
)

teacher_router = APIRouter(prefix="/api/v1/teacher", tags=["teacher"])


@teacher_router.get("/dashboard", response_model=TeacherDashboardResponse)
async def teacher_dashboard_endpoint(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:manage_classes")),  # noqa: B008
) -> TeacherDashboardResponse:
    return await get_teacher_dashboard(db, caller)


@teacher_router.post(
    "/classes",
    response_model=TeacherClassResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_class_endpoint(
    payload: TeacherClassCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:manage_classes")),  # noqa: B008
) -> TeacherClassResponse:
    return await create_teacher_class(db, caller, payload)


@teacher_router.get("/classes/{class_id}/sections", response_model=list[TeacherSectionResponse])
async def list_sections_endpoint(
    class_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:manage_classes")),  # noqa: B008
) -> list[TeacherSectionResponse]:
    return await list_sections(db, caller, class_id)


@teacher_router.post(
    "/classes/{class_id}/sections",
    response_model=TeacherSectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_section_endpoint(
    class_id: UUID,
    payload: TeacherSectionCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:manage_classes")),  # noqa: B008
) -> TeacherSectionResponse:
    return await create_section(db, caller, class_id, payload)


@teacher_router.get("/classes/{class_id}/students", response_model=list[ClassEnrollmentResponse])
async def list_class_students_endpoint(
    class_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:manage_classes")),  # noqa: B008
) -> list[ClassEnrollmentResponse]:
    return await list_class_students(db, caller, class_id)


@teacher_router.post(
    "/classes/{class_id}/students",
    response_model=ClassEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_student_endpoint(
    class_id: UUID,
    payload: ClassEnrollStudentRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:manage_classes")),  # noqa: B008
) -> ClassEnrollmentResponse:
    return await enroll_student_in_class(db, caller, class_id, payload)


@teacher_router.get("/question-bank", response_model=list[QuestionBankOptionItem])
async def question_bank_selector_endpoint(
    subject_id: UUID | None = Query(default=None),
    chapter_id: UUID | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    _caller: AuthenticatedUser = Depends(require_permissions("teacher:manage_classes")),  # noqa: B008
) -> list[QuestionBankOptionItem]:
    return await list_question_bank_options(
        db, subject_id=subject_id, chapter_id=chapter_id, limit=limit
    )


@teacher_router.get("/assignments", response_model=list[TeacherAssignmentResponse])
async def list_assignments_endpoint(
    class_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:manage_classes")),  # noqa: B008
) -> list[TeacherAssignmentResponse]:
    return await list_assignments(db, caller, class_id=class_id)


@teacher_router.post(
    "/assignments",
    response_model=TeacherAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment_endpoint(
    payload: TeacherAssignmentCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:manage_classes")),  # noqa: B008
) -> TeacherAssignmentResponse:
    return await create_assignment(db, caller, payload)


@teacher_router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=AssignmentSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_assignment_endpoint(
    assignment_id: UUID,
    payload: StudentAssignmentSubmitRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_roles("student")),  # noqa: B008
) -> AssignmentSubmissionResponse:
    return await submit_assignment_as_student(db, caller, assignment_id, payload)


@teacher_router.get(
    "/assignments/{assignment_id}/submissions",
    response_model=list[AssignmentSubmissionResponse],
)
async def list_submissions_endpoint(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:grade_submissions")),  # noqa: B008
) -> list[AssignmentSubmissionResponse]:
    return await list_assignment_submissions(db, caller, assignment_id)


@teacher_router.post(
    "/submissions/{submission_id}/ai-grade",
    response_model=AssignmentSubmissionResponse,
)
async def ai_grade_submission_endpoint(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:grade_submissions")),  # noqa: B008
) -> AssignmentSubmissionResponse:
    return await run_ai_assisted_grade(db, caller, submission_id)


@teacher_router.patch(
    "/submissions/{submission_id}/override",
    response_model=AssignmentSubmissionResponse,
)
async def teacher_override_endpoint(
    submission_id: UUID,
    payload: TeacherOverrideGradeRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:grade_submissions")),  # noqa: B008
) -> AssignmentSubmissionResponse:
    return await override_submission_grade(db, caller, submission_id, payload)


@teacher_router.get(
    "/classes/{class_id}/analytics",
    response_model=TeacherClassAnalyticsResponse,
)
async def class_analytics_endpoint(
    class_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:view_analytics")),  # noqa: B008
) -> TeacherClassAnalyticsResponse:
    return await get_class_analytics(db, caller, class_id)


@teacher_router.get(
    "/students/{student_id}/analytics",
    response_model=TeacherStudentAnalyticsResponse,
)
async def student_analytics_endpoint(
    student_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:view_analytics")),  # noqa: B008
) -> TeacherStudentAnalyticsResponse:
    return await get_student_analytics_for_teacher(db, caller, student_id)


@teacher_router.get("/classes/{class_id}/report.csv")
async def export_class_report_endpoint(
    class_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("teacher:view_analytics")),  # noqa: B008
) -> Response:
    filename, csv_body = await export_class_report_csv(db, caller, class_id)
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
