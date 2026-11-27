"""Service layer for Teacher Ecosystem (F-031).

Enforces strict backend authorization:
- Teachers can only view/modify classes they own (or within their tenant for school_admin/platform_admin).
- Teachers can only inspect student analytics for students actively enrolled in their classes.
- Teacher Override always supersedes AI-assisted draft scores and records an immutable audit log.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.errors import AppError
from src.modules.assessment.public import get_student_progress_snapshot
from src.modules.identity.public import get_user_displays_map, resolve_user_by_email
from src.modules.learning.public import (
    get_concept_mastery_scores_map,
    list_weak_concept_summaries,
)
from src.modules.question_bank.public import list_published_questions_for_practice
from src.modules.teacher.logic import (
    compute_ai_grading_draft,
    render_safe_csv_report,
    validate_teacher_override_score,
)
from src.modules.teacher.models import (
    AssignmentSubmission,
    ClassEnrollment,
    TeacherAssignment,
    TeacherClass,
    TeacherSection,
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
    WeakConceptItem,
)


def _is_privileged_admin(caller: AuthenticatedUser) -> bool:
    return caller.has_role("platform_admin") or caller.has_role("school_admin")


async def _require_class_access(
    db: AsyncSession, caller: AuthenticatedUser, class_id: UUID
) -> TeacherClass:
    tclass = await db.get(TeacherClass, class_id)
    if tclass is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="CLASS_NOT_FOUND",
            message="Class not found.",
        )
    if caller.has_role("platform_admin"):
        return tclass
    if caller.has_role("school_admin") and caller.tenant_id and tclass.tenant_id == caller.tenant_id:
        return tclass
    if tclass.teacher_id != caller.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="TEACHER_CLASS_FORBIDDEN",
            message="You are not authorized to access or manage this class.",
        )
    if caller.tenant_id and tclass.tenant_id and tclass.tenant_id != caller.tenant_id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CROSS_TENANT_FORBIDDEN",
            message="Cross-tenant class access is forbidden.",
        )
    return tclass


async def _assert_teacher_authorized_for_student(
    db: AsyncSession, caller: AuthenticatedUser, student_id: UUID
) -> list[UUID]:
    """Verify student is enrolled in at least one class managed by caller; return class IDs."""
    stmt = (
        select(ClassEnrollment.class_id)
        .join(TeacherClass, TeacherClass.id == ClassEnrollment.class_id)
        .where(
            ClassEnrollment.student_id == student_id,
            ClassEnrollment.status == "active",
        )
    )
    if caller.has_role("platform_admin"):
        pass
    elif caller.has_role("school_admin") and caller.tenant_id:
        stmt = stmt.where(TeacherClass.tenant_id == caller.tenant_id)
    else:
        stmt = stmt.where(TeacherClass.teacher_id == caller.id)
        if caller.tenant_id:
            stmt = stmt.where(
                (TeacherClass.tenant_id == caller.tenant_id) | (TeacherClass.tenant_id.is_(None))
            )

    class_ids = list((await db.scalars(stmt)).all())
    if not class_ids and not caller.has_role("platform_admin"):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="TEACHER_STUDENT_FORBIDDEN",
            message="Teachers may only access analytics for students enrolled in their classes.",
        )
    return class_ids


async def _serialize_class(db: AsyncSession, tclass: TeacherClass) -> TeacherClassResponse:
    sections_count = int(
        await db.scalar(
            select(func.count(TeacherSection.id)).where(TeacherSection.class_id == tclass.id)
        )
        or 0
    )
    students_count = int(
        await db.scalar(
            select(func.count(ClassEnrollment.id)).where(
                ClassEnrollment.class_id == tclass.id,
                ClassEnrollment.status == "active",
            )
        )
        or 0
    )
    assignments_count = int(
        await db.scalar(
            select(func.count(TeacherAssignment.id)).where(
                TeacherAssignment.class_id == tclass.id
            )
        )
        or 0
    )
    return TeacherClassResponse(
        id=tclass.id,
        tenant_id=tclass.tenant_id,
        teacher_id=tclass.teacher_id,
        name=tclass.name,
        grade_label=tclass.grade_label,
        subject_name=tclass.subject_name,
        status=tclass.status,
        sections_count=sections_count,
        students_count=students_count,
        assignments_count=assignments_count,
        created_at=tclass.created_at,
    )


async def _serialize_assignment(
    db: AsyncSession, assignment: TeacherAssignment
) -> TeacherAssignmentResponse:
    subs_count = int(
        await db.scalar(
            select(func.count(AssignmentSubmission.id)).where(
                AssignmentSubmission.assignment_id == assignment.id
            )
        )
        or 0
    )
    graded_count = int(
        await db.scalar(
            select(func.count(AssignmentSubmission.id)).where(
                AssignmentSubmission.assignment_id == assignment.id,
                AssignmentSubmission.status.in_(["teacher_reviewed", "returned"]),
            )
        )
        or 0
    )
    return TeacherAssignmentResponse(
        id=assignment.id,
        class_id=assignment.class_id,
        section_id=assignment.section_id,
        teacher_id=assignment.teacher_id,
        title=assignment.title,
        instructions=assignment.instructions,
        assignment_type=assignment.assignment_type,
        question_ids=[str(q) for q in (assignment.question_ids_jsonb or [])],
        max_marks=float(assignment.max_marks),
        due_at=assignment.due_at,
        status=assignment.status,
        submissions_count=subs_count,
        graded_count=graded_count,
        created_at=assignment.created_at,
    )


async def get_teacher_dashboard(
    db: AsyncSession, caller: AuthenticatedUser
) -> TeacherDashboardResponse:
    stmt = select(TeacherClass).order_by(TeacherClass.created_at.desc())
    if not caller.has_role("platform_admin"):
        if caller.has_role("school_admin") and caller.tenant_id:
            stmt = stmt.where(TeacherClass.tenant_id == caller.tenant_id)
        else:
            stmt = stmt.where(TeacherClass.teacher_id == caller.id)
    classes = (await db.scalars(stmt)).all()
    class_items = [await _serialize_class(db, c) for c in classes]
    class_ids = [c.id for c in classes]

    if class_ids:
        distinct_students = int(
            await db.scalar(
                select(func.count(func.distinct(ClassEnrollment.student_id))).where(
                    ClassEnrollment.class_id.in_(class_ids),
                    ClassEnrollment.status == "active",
                )
            )
            or 0
        )
        assignments = (
            await db.scalars(
                select(TeacherAssignment)
                .where(TeacherAssignment.class_id.in_(class_ids))
                .order_by(TeacherAssignment.created_at.desc())
                .limit(20)
            )
        ).all()
        assignment_ids = [a.id for a in assignments]
        pending_reviews = (
            int(
                await db.scalar(
                    select(func.count(AssignmentSubmission.id)).where(
                        AssignmentSubmission.assignment_id.in_(assignment_ids),
                        AssignmentSubmission.status.in_(["submitted", "ai_graded"]),
                    )
                )
                or 0
            )
            if assignment_ids
            else 0
        )
        recent_assignments = [await _serialize_assignment(db, a) for a in assignments]
    else:
        distinct_students = 0
        pending_reviews = 0
        recent_assignments = []

    return TeacherDashboardResponse(
        teacher_id=caller.id,
        total_classes=len(class_items),
        total_students=distinct_students,
        total_assignments=sum(c.assignments_count for c in class_items),
        pending_reviews_count=pending_reviews,
        classes=class_items,
        recent_assignments=recent_assignments,
    )


async def create_teacher_class(
    db: AsyncSession, caller: AuthenticatedUser, payload: TeacherClassCreateRequest
) -> TeacherClassResponse:
    tclass = TeacherClass(
        tenant_id=caller.tenant_id,
        school_id=payload.school_id,
        branch_id=payload.branch_id,
        academic_year_id=payload.academic_year_id,
        teacher_id=caller.id,
        name=payload.name.strip(),
        grade_label=payload.grade_label.strip(),
        subject_name=payload.subject_name.strip(),
        status="active",
    )
    db.add(tclass)
    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "teacher",
        action="teacher_class.created",
        resource_type="teacher_class",
        resource_id=str(tclass.id),
        tenant_id=caller.tenant_id,
    )
    await db.commit()
    await db.refresh(tclass)
    return await _serialize_class(db, tclass)


async def list_sections(
    db: AsyncSession, caller: AuthenticatedUser, class_id: UUID
) -> list[TeacherSectionResponse]:
    await _require_class_access(db, caller, class_id)
    sections = (
        await db.scalars(
            select(TeacherSection)
            .where(TeacherSection.class_id == class_id)
            .order_by(TeacherSection.code.asc())
        )
    ).all()
    results: list[TeacherSectionResponse] = []
    for sec in sections:
        enrolled = int(
            await db.scalar(
                select(func.count(ClassEnrollment.id)).where(
                    ClassEnrollment.section_id == sec.id,
                    ClassEnrollment.status == "active",
                )
            )
            or 0
        )
        results.append(
            TeacherSectionResponse(
                id=sec.id,
                class_id=sec.class_id,
                name=sec.name,
                code=sec.code,
                capacity=sec.capacity,
                enrolled_count=enrolled,
            )
        )
    return results


async def create_section(
    db: AsyncSession,
    caller: AuthenticatedUser,
    class_id: UUID,
    payload: TeacherSectionCreateRequest,
) -> TeacherSectionResponse:
    tclass = await _require_class_access(db, caller, class_id)
    code_norm = payload.code.strip().upper()
    existing = await db.scalar(
        select(TeacherSection).where(
            TeacherSection.class_id == class_id,
            TeacherSection.code == code_norm,
        )
    )
    if existing is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code="SECTION_CODE_EXISTS",
            message=f"Section code '{code_norm}' already exists in this class.",
        )
    sec = TeacherSection(
        tenant_id=tclass.tenant_id,
        class_id=class_id,
        name=payload.name.strip(),
        code=code_norm,
        capacity=payload.capacity,
    )
    db.add(sec)
    await db.commit()
    await db.refresh(sec)
    return TeacherSectionResponse(
        id=sec.id,
        class_id=sec.class_id,
        name=sec.name,
        code=sec.code,
        capacity=sec.capacity,
        enrolled_count=0,
    )


async def list_class_students(
    db: AsyncSession, caller: AuthenticatedUser, class_id: UUID
) -> list[ClassEnrollmentResponse]:
    await _require_class_access(db, caller, class_id)
    enrollments = (
        await db.scalars(
            select(ClassEnrollment)
            .where(ClassEnrollment.class_id == class_id, ClassEnrollment.status == "active")
            .order_by(ClassEnrollment.enrolled_at.desc())
        )
    ).all()
    sections = (
        await db.scalars(select(TeacherSection).where(TeacherSection.class_id == class_id))
    ).all()
    section_names = {s.id: s.name for s in sections}
    displays = await get_user_displays_map(db, [e.student_id for e in enrollments])
    return [
        ClassEnrollmentResponse(
            id=e.id,
            class_id=e.class_id,
            section_id=e.section_id,
            section_name=section_names.get(e.section_id) if e.section_id else None,
            student_id=e.student_id,
            student_name=displays[e.student_id].display_name
            if e.student_id in displays
            else "Student",
            student_email=displays[e.student_id].email if e.student_id in displays else "",
            roll_no=e.roll_no,
            status=e.status,
            enrolled_at=e.enrolled_at,
        )
        for e in enrollments
    ]


async def enroll_student_in_class(
    db: AsyncSession,
    caller: AuthenticatedUser,
    class_id: UUID,
    payload: ClassEnrollStudentRequest,
) -> ClassEnrollmentResponse:
    tclass = await _require_class_access(db, caller, class_id)
    student = await resolve_user_by_email(db, payload.student_email)
    if student is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="STUDENT_NOT_FOUND",
            message="No active student account matches that email.",
        )
    section_name: str | None = None
    if payload.section_id is not None:
        sec = await db.get(TeacherSection, payload.section_id)
        if sec is None or sec.class_id != class_id:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_SECTION",
                message="Selected section does not belong to this class.",
            )
        section_name = sec.name

    existing = await db.scalar(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.student_id == student.user_id,
        )
    )
    if existing is not None:
        existing.status = "active"
        existing.section_id = payload.section_id
        existing.roll_no = payload.roll_no
        enrollment = existing
    else:
        enrollment = ClassEnrollment(
            tenant_id=tclass.tenant_id,
            class_id=class_id,
            section_id=payload.section_id,
            student_id=student.user_id,
            roll_no=payload.roll_no,
            status="active",
        )
        db.add(enrollment)

    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "teacher",
        action="class_enrollment.upserted",
        resource_type="class_enrollment",
        resource_id=str(enrollment.id),
        tenant_id=tclass.tenant_id,
        metadata={"class_id": str(class_id), "student_id": str(student.user_id)},
    )
    await db.commit()
    await db.refresh(enrollment)
    return ClassEnrollmentResponse(
        id=enrollment.id,
        class_id=enrollment.class_id,
        section_id=enrollment.section_id,
        section_name=section_name,
        student_id=student.user_id,
        student_name=student.display_name,
        student_email=student.email,
        roll_no=enrollment.roll_no,
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at,
    )


async def list_question_bank_options(
    db: AsyncSession,
    *,
    subject_id: UUID | None = None,
    chapter_id: UUID | None = None,
    limit: int = 30,
) -> list[QuestionBankOptionItem]:
    questions = await list_published_questions_for_practice(
        db, subject_id=subject_id, chapter_id=chapter_id, limit=min(max(limit, 1), 100)
    )
    return [
        QuestionBankOptionItem(
            question_id=q.question_id,
            question_version_id=q.question_version_id,
            question_type=q.question_type,
            difficulty=q.difficulty,
            default_marks=q.default_marks,
            stem_preview=q.stem_markdown[:180],
        )
        for q in questions
    ]


async def create_assignment(
    db: AsyncSession,
    caller: AuthenticatedUser,
    payload: TeacherAssignmentCreateRequest,
) -> TeacherAssignmentResponse:
    tclass = await _require_class_access(db, caller, payload.class_id)
    if payload.section_id is not None:
        sec = await db.get(TeacherSection, payload.section_id)
        if sec is None or sec.class_id != tclass.id:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_SECTION",
                message="Section does not belong to the selected class.",
            )
    assignment = TeacherAssignment(
        tenant_id=tclass.tenant_id,
        class_id=tclass.id,
        section_id=payload.section_id,
        teacher_id=caller.id,
        title=payload.title.strip(),
        instructions=payload.instructions.strip(),
        assignment_type=payload.assignment_type,
        question_ids_jsonb=[str(qid) for qid in payload.question_ids],
        max_marks=payload.max_marks,
        due_at=payload.due_at,
        status=payload.status,
    )
    db.add(assignment)
    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "teacher",
        action="teacher_assignment.created",
        resource_type="teacher_assignment",
        resource_id=str(assignment.id),
        tenant_id=tclass.tenant_id,
        metadata={"assignment_type": assignment.assignment_type, "max_marks": assignment.max_marks},
    )
    await db.commit()
    await db.refresh(assignment)
    return await _serialize_assignment(db, assignment)


async def list_assignments(
    db: AsyncSession, caller: AuthenticatedUser, class_id: UUID | None = None
) -> list[TeacherAssignmentResponse]:
    if class_id is not None:
        await _require_class_access(db, caller, class_id)
        rows = (
            await db.scalars(
                select(TeacherAssignment)
                .where(TeacherAssignment.class_id == class_id)
                .order_by(TeacherAssignment.created_at.desc())
            )
        ).all()
    else:
        stmt = select(TeacherAssignment).order_by(TeacherAssignment.created_at.desc())
        if not caller.has_role("platform_admin"):
            if caller.has_role("school_admin") and caller.tenant_id:
                stmt = stmt.where(TeacherAssignment.tenant_id == caller.tenant_id)
            else:
                stmt = stmt.where(TeacherAssignment.teacher_id == caller.id)
        rows = (await db.scalars(stmt.limit(100))).all()
    return [await _serialize_assignment(db, a) for a in rows]


async def submit_assignment_as_student(
    db: AsyncSession,
    caller: AuthenticatedUser,
    assignment_id: UUID,
    payload: StudentAssignmentSubmitRequest,
) -> AssignmentSubmissionResponse:
    assignment = await db.get(TeacherAssignment, assignment_id)
    if assignment is None or assignment.status != "published":
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ASSIGNMENT_NOT_FOUND",
            message="Published assignment not found.",
        )
    enrollment = await db.scalar(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == assignment.class_id,
            ClassEnrollment.student_id == caller.id,
            ClassEnrollment.status == "active",
        )
    )
    if enrollment is None:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="NOT_ENROLLED_IN_CLASS",
            message="You must be enrolled in this class to submit this assignment.",
        )

    existing = await db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.student_id == caller.id,
        )
    )
    if existing is not None:
        existing.response_text = payload.response_text.strip()
        existing.homework_submission_id = payload.homework_submission_id
        existing.status = "submitted"
        submission = existing
    else:
        submission = AssignmentSubmission(
            tenant_id=assignment.tenant_id,
            assignment_id=assignment.id,
            student_id=caller.id,
            homework_submission_id=payload.homework_submission_id,
            response_text=payload.response_text.strip(),
            status="submitted",
        )
        db.add(submission)

    await db.commit()
    await db.refresh(submission)
    displays = await get_user_displays_map(db, [caller.id])
    disp = displays.get(caller.id)
    return _serialize_submission(submission, assignment=assignment, student_name=disp.display_name if disp else "Student", student_email=disp.email if disp else caller.email)


def _serialize_submission(
    sub: AssignmentSubmission,
    *,
    assignment: TeacherAssignment,
    student_name: str,
    student_email: str,
) -> AssignmentSubmissionResponse:
    effective = sub.teacher_score if sub.teacher_score is not None else sub.ai_suggested_score
    return AssignmentSubmissionResponse(
        id=sub.id,
        assignment_id=sub.assignment_id,
        student_id=sub.student_id,
        student_name=student_name,
        student_email=student_email,
        response_text=sub.response_text,
        ai_suggested_score=sub.ai_suggested_score,
        ai_feedback_summary=sub.ai_feedback_summary,
        teacher_score=sub.teacher_score,
        teacher_override_reason=sub.teacher_override_reason,
        teacher_feedback=sub.teacher_feedback,
        effective_score=effective,
        max_marks=float(assignment.max_marks),
        status=sub.status,
        graded_by=sub.graded_by,
        graded_at=sub.graded_at,
        created_at=sub.created_at,
    )


async def list_assignment_submissions(
    db: AsyncSession, caller: AuthenticatedUser, assignment_id: UUID
) -> list[AssignmentSubmissionResponse]:
    assignment = await db.get(TeacherAssignment, assignment_id)
    if assignment is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ASSIGNMENT_NOT_FOUND",
            message="Assignment not found.",
        )
    await _require_class_access(db, caller, assignment.class_id)
    subs = (
        await db.scalars(
            select(AssignmentSubmission)
            .where(AssignmentSubmission.assignment_id == assignment_id)
            .order_by(AssignmentSubmission.created_at.desc())
        )
    ).all()
    displays = await get_user_displays_map(db, [s.student_id for s in subs])
    return [
        _serialize_submission(
            s,
            assignment=assignment,
            student_name=displays[s.student_id].display_name if s.student_id in displays else "Student",
            student_email=displays[s.student_id].email if s.student_id in displays else "",
        )
        for s in subs
    ]


async def run_ai_assisted_grade(
    db: AsyncSession, caller: AuthenticatedUser, submission_id: UUID
) -> AssignmentSubmissionResponse:
    sub = await db.get(AssignmentSubmission, submission_id)
    if sub is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SUBMISSION_NOT_FOUND",
            message="Assignment submission not found.",
        )
    assignment = await db.get(TeacherAssignment, sub.assignment_id)
    if assignment is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ASSIGNMENT_NOT_FOUND",
            message="Parent assignment not found.",
        )
    await _require_class_access(db, caller, assignment.class_id)

    draft = compute_ai_grading_draft(
        response_text=sub.response_text,
        instructions=assignment.instructions,
        max_marks=float(assignment.max_marks),
    )
    sub.ai_suggested_score = draft.suggested_score
    sub.ai_feedback_summary = draft.feedback_summary
    if sub.status == "submitted":
        sub.status = "ai_graded"

    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "teacher",
        action="assignment_submission.ai_graded",
        resource_type="assignment_submission",
        resource_id=str(sub.id),
        tenant_id=assignment.tenant_id,
        metadata={"ai_suggested_score": draft.suggested_score, "rubric_band": draft.rubric_band},
    )
    await db.commit()
    await db.refresh(sub)
    displays = await get_user_displays_map(db, [sub.student_id])
    disp = displays.get(sub.student_id)
    return _serialize_submission(
        sub,
        assignment=assignment,
        student_name=disp.display_name if disp else "Student",
        student_email=disp.email if disp else "",
    )


async def override_submission_grade(
    db: AsyncSession,
    caller: AuthenticatedUser,
    submission_id: UUID,
    payload: TeacherOverrideGradeRequest,
) -> AssignmentSubmissionResponse:
    sub = await db.get(AssignmentSubmission, submission_id)
    if sub is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SUBMISSION_NOT_FOUND",
            message="Assignment submission not found.",
        )
    assignment = await db.get(TeacherAssignment, sub.assignment_id)
    if assignment is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ASSIGNMENT_NOT_FOUND",
            message="Parent assignment not found.",
        )
    await _require_class_access(db, caller, assignment.class_id)

    try:
        validated_score = validate_teacher_override_score(
            score=payload.teacher_score,
            max_marks=float(assignment.max_marks),
        )
    except ValueError as exc:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_SCORE_RANGE",
            message=str(exc),
        ) from exc

    sub.teacher_score = validated_score
    sub.teacher_feedback = payload.teacher_feedback.strip()
    sub.teacher_override_reason = (
        payload.teacher_override_reason.strip() if payload.teacher_override_reason else None
    )
    sub.status = payload.status
    sub.graded_by = caller.id
    sub.graded_at = datetime.now(UTC)

    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "teacher",
        action="assignment_submission.teacher_override",
        resource_type="assignment_submission",
        resource_id=str(sub.id),
        tenant_id=assignment.tenant_id,
        metadata={
            "ai_suggested_score": sub.ai_suggested_score,
            "teacher_score": validated_score,
            "max_marks": float(assignment.max_marks),
        },
    )
    await db.commit()
    await db.refresh(sub)
    displays = await get_user_displays_map(db, [sub.student_id])
    disp = displays.get(sub.student_id)
    return _serialize_submission(
        sub,
        assignment=assignment,
        student_name=disp.display_name if disp else "Student",
        student_email=disp.email if disp else "",
    )


async def get_class_analytics(
    db: AsyncSession, caller: AuthenticatedUser, class_id: UUID
) -> TeacherClassAnalyticsResponse:
    tclass = await _require_class_access(db, caller, class_id)
    enrollments = (
        await db.scalars(
            select(ClassEnrollment).where(
                ClassEnrollment.class_id == class_id,
                ClassEnrollment.status == "active",
            )
        )
    ).all()
    student_ids = [e.student_id for e in enrollments]
    assignments = (
        await db.scalars(
            select(TeacherAssignment).where(TeacherAssignment.class_id == class_id)
        )
    ).all()
    assignment_map = {a.id: a for a in assignments}
    subs = (
        (
            await db.scalars(
                select(AssignmentSubmission).where(
                    AssignmentSubmission.assignment_id.in_(list(assignment_map.keys()))
                )
            )
        ).all()
        if assignment_map
        else []
    )

    score_pcts: list[float] = []
    graded_count = 0
    for s in subs:
        effective = s.teacher_score if s.teacher_score is not None else s.ai_suggested_score
        if s.status in ("teacher_reviewed", "returned"):
            graded_count += 1
        asgn = assignment_map.get(s.assignment_id)
        if effective is not None and asgn and asgn.max_marks > 0:
            score_pcts.append((effective / float(asgn.max_marks)) * 100.0)

    mastery_all: list[float] = []
    weak_scores_by_concept: dict[UUID, list[float]] = defaultdict(list)
    for sid in student_ids:
        scores = await get_concept_mastery_scores_map(db, sid)
        mastery_all.extend(scores.values())
        weak_rows = await list_weak_concept_summaries(db, sid, threshold=60.0)
        for w in weak_rows:
            weak_scores_by_concept[w.concept_id].append(w.mastery_score)

    weak_concepts = [
        WeakConceptItem(
            concept_id=cid,
            average_mastery_pct=round(sum(vals) / len(vals), 2),
            affected_students_count=len(vals),
        )
        for cid, vals in sorted(
            weak_scores_by_concept.items(),
            key=lambda kv: (-len(kv[1]), sum(kv[1]) / len(kv[1])),
        )[:10]
    ]

    return TeacherClassAnalyticsResponse(
        class_id=tclass.id,
        class_name=tclass.name,
        total_students=len(student_ids),
        total_assignments=len(assignments),
        total_submissions=len(subs),
        graded_submissions=graded_count,
        average_score_pct=round(sum(score_pcts) / len(score_pcts), 2) if score_pcts else 0.0,
        average_mastery_pct=round(sum(mastery_all) / len(mastery_all), 2) if mastery_all else 0.0,
        weak_concepts=weak_concepts,
    )


async def get_student_analytics_for_teacher(
    db: AsyncSession, caller: AuthenticatedUser, student_id: UUID
) -> TeacherStudentAnalyticsResponse:
    class_ids = await _assert_teacher_authorized_for_student(db, caller, student_id)
    displays = await get_user_displays_map(db, [student_id])
    disp = displays.get(student_id)

    progress = await get_student_progress_snapshot(db, student_id)
    accuracy_pct = (
        round((progress.correct_attempts / progress.total_attempts) * 100.0, 2)
        if progress.total_attempts
        else 0.0
    )
    mastery_map = await get_concept_mastery_scores_map(db, student_id)
    mastery_avg = (
        round(sum(mastery_map.values()) / len(mastery_map), 2) if mastery_map else 0.0
    )
    weak_rows = await list_weak_concept_summaries(db, student_id, threshold=60.0)

    assignments = (
        (
            await db.scalars(
                select(TeacherAssignment).where(TeacherAssignment.class_id.in_(class_ids))
            )
        ).all()
        if class_ids
        else []
    )
    asgn_map = {a.id: a for a in assignments}
    subs = (
        (
            await db.scalars(
                select(AssignmentSubmission).where(
                    AssignmentSubmission.assignment_id.in_(list(asgn_map.keys())),
                    AssignmentSubmission.student_id == student_id,
                )
            )
        ).all()
        if asgn_map
        else []
    )
    sub_pcts: list[float] = []
    for s in subs:
        eff = s.teacher_score if s.teacher_score is not None else s.ai_suggested_score
        asgn = asgn_map.get(s.assignment_id)
        if eff is not None and asgn and asgn.max_marks > 0:
            sub_pcts.append((eff / float(asgn.max_marks)) * 100.0)

    return TeacherStudentAnalyticsResponse(
        student_id=student_id,
        student_name=disp.display_name if disp else "Student",
        student_email=disp.email if disp else "",
        enrolled_classes_count=len(class_ids),
        practice_total_attempts=progress.total_attempts,
        practice_accuracy_pct=accuracy_pct,
        mastery_average_pct=mastery_avg,
        weak_concepts=[
            WeakConceptItem(
                concept_id=w.concept_id,
                average_mastery_pct=w.mastery_score,
                affected_students_count=1,
            )
            for w in weak_rows[:10]
        ],
        submissions_total=len(subs),
        submissions_average_pct=round(sum(sub_pcts) / len(sub_pcts), 2) if sub_pcts else 0.0,
    )


async def export_class_report_csv(
    db: AsyncSession, caller: AuthenticatedUser, class_id: UUID
) -> tuple[str, str]:
    tclass = await _require_class_access(db, caller, class_id)
    enrollments = (
        await db.scalars(
            select(ClassEnrollment).where(
                ClassEnrollment.class_id == class_id,
                ClassEnrollment.status == "active",
            )
        )
    ).all()
    displays = await get_user_displays_map(db, [e.student_id for e in enrollments])
    assignments = (
        await db.scalars(
            select(TeacherAssignment).where(TeacherAssignment.class_id == class_id)
        )
    ).all()
    asgn_map = {a.id: a for a in assignments}
    subs = (
        (
            await db.scalars(
                select(AssignmentSubmission).where(
                    AssignmentSubmission.assignment_id.in_(list(asgn_map.keys()))
                )
            )
        ).all()
        if asgn_map
        else []
    )
    subs_by_student: dict[UUID, list[AssignmentSubmission]] = defaultdict(list)
    for s in subs:
        subs_by_student[s.student_id].append(s)

    headers = [
        "Class",
        "Student Name",
        "Student Email",
        "Roll No",
        "Submissions",
        "Average Score (%)",
        "Practice Accuracy (%)",
        "Average Mastery (%)",
    ]
    rows: list[list[object]] = []
    for e in enrollments:
        disp = displays.get(e.student_id)
        progress = await get_student_progress_snapshot(db, e.student_id)
        acc = (
            round((progress.correct_attempts / progress.total_attempts) * 100.0, 2)
            if progress.total_attempts
            else 0.0
        )
        mastery_map = await get_concept_mastery_scores_map(db, e.student_id)
        mastery_avg = (
            round(sum(mastery_map.values()) / len(mastery_map), 2) if mastery_map else 0.0
        )
        stu_subs = subs_by_student.get(e.student_id, [])
        pcts = [
            ((s.teacher_score if s.teacher_score is not None else s.ai_suggested_score) / float(asgn_map[s.assignment_id].max_marks)) * 100.0
            for s in stu_subs
            if (s.teacher_score is not None or s.ai_suggested_score is not None)
            and s.assignment_id in asgn_map
            and asgn_map[s.assignment_id].max_marks > 0
        ]
        avg_score = round(sum(pcts) / len(pcts), 2) if pcts else 0.0
        rows.append(
            [
                tclass.name,
                disp.display_name if disp else "Student",
                disp.email if disp else "",
                e.roll_no or "",
                len(stu_subs),
                avg_score,
                acc,
                mastery_avg,
            ]
        )

    csv_body = render_safe_csv_report(headers, rows)
    safe_slug = "".join(ch if ch.isalnum() else "_" for ch in tclass.name.lower())[:40]
    return f"go4guru_class_report_{safe_slug}.csv", csv_body
