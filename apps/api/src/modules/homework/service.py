"""Service layer for Phase 6 Homework AI (F-029): uploads, OCR, evaluation, hints & retries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.config import Settings
from src.core.errors import AppError
from src.core.outbox import OutboxEvent
from src.core.storage import LocalPrivateStorage
from src.modules.ai.public import AIRouterGateway, scrub_pii_text
from src.modules.homework.evaluator import (
    EvaluationDraft,
    classify_confidence_band,
    evaluate_homework_submission,
)
from src.modules.homework.file_security import (
    FileValidationError,
    ValidatedHomeworkFile,
    build_private_homework_storage_key,
    validate_and_sanitize_upload,
)
from src.modules.homework.models import (
    HomeworkEvaluation,
    HomeworkFile,
    HomeworkOcrResult,
    HomeworkSubmission,
)
from src.modules.homework.ocr import HomeworkOcrPipeline
from src.modules.homework.schemas import (
    ErrorClassificationOut,
    ExtractedStepOut,
    FeedbackValidationReportOut,
    GraduatedHintOut,
    HomeworkEvaluationOut,
    HomeworkFileOut,
    HomeworkOcrPageOut,
    HomeworkRetryRequest,
    HomeworkSubmissionDetailOut,
    HomeworkSubmissionSummaryOut,
    HomeworkSubjectArea,
    HomeworkSubjectSelection,
    OcrCorrectionRequest,
    RevisionRecommendationOut,
    StepEvaluationOut,
)
from src.modules.notifications.public import emit_in_app_notification

MAX_HINT_LEVEL = 3


def _assert_submission_access(
    submission: HomeworkSubmission | None,
    caller: AuthenticatedUser,
    *,
    require_owner: bool = False,
) -> HomeworkSubmission:
    """Enforce ownership and RBAC boundaries (parents are strictly excluded)."""
    if submission is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="HOMEWORK_SUBMISSION_NOT_FOUND",
            message="Homework submission not found.",
        )

    is_owner = submission.student_id == caller.id
    can_review = caller.has_permission("homework:review") and not require_owner

    if not is_owner and not can_review:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="HOMEWORK_ACCESS_DENIED",
            message="You do not have permission to access this homework submission.",
        )

    # Tenant isolation check for institutional reviewers
    if (
        not is_owner
        and submission.tenant_id is not None
        and caller.tenant_id is not None
        and submission.tenant_id != caller.tenant_id
        and not caller.has_role("platform_admin")
    ):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CROSS_TENANT_ACCESS_DENIED",
            message="Cross-tenant homework access is prohibited.",
        )

    return submission


def _serialize_file(file_row: HomeworkFile) -> HomeworkFileOut:
    return HomeworkFileOut(
        id=file_row.id,
        page_no=file_row.page_no,
        original_filename=file_row.original_filename,
        mime_type=file_row.mime_type,
        detected_format=file_row.detected_format,
        size_bytes=file_row.size_bytes,
        sha256=file_row.sha256,
        exif_stripped=file_row.exif_stripped,
        pdf_page_count=file_row.pdf_page_count,
        scan_status=file_row.scan_status,
        download_url=f"/api/v1/homework/submissions/{file_row.submission_id}/files/{file_row.id}",
        created_at=file_row.created_at,
    )


def _serialize_ocr_page(row: HomeworkOcrResult) -> HomeworkOcrPageOut:
    effective = (row.student_corrected_text or row.extracted_text or "").strip()
    return HomeworkOcrPageOut(
        id=row.id,
        page_no=row.page_no,
        ocr_provider=row.ocr_provider,
        extracted_text=row.extracted_text,
        extracted_latex=row.extracted_latex,
        handwriting_detected=row.handwriting_detected,
        handwriting_supported=row.handwriting_supported,
        confidence=round(float(row.confidence), 3),
        needs_review=row.needs_review,
        student_corrected_text=row.student_corrected_text,
        effective_text=effective,
        warnings=[str(w) for w in (row.warnings_jsonb or [])],
    )


def _serialize_evaluation(row: HomeworkEvaluation) -> HomeworkEvaluationOut:
    """Serialize evaluation enforcing anti-spoiler guard (hide locked hints & unrevealed solution)."""
    all_hints = [GraduatedHintOut.model_validate(h) for h in (row.hints_jsonb or [])]
    unlocked_level = max(0, min(MAX_HINT_LEVEL, int(row.current_hint_level_unlocked)))
    unlocked_hints = [h for h in all_hints if h.level <= unlocked_level]
    max_level = max((h.level for h in all_hints), default=MAX_HINT_LEVEL)

    validation_raw = row.validation_report_jsonb or {
        "passed": True,
        "spoiler_guard_passed": True,
        "taxonomy_valid": True,
        "verifier_agreement": "not_applicable",
        "safety_passed": True,
        "confidence_adjusted": False,
        "issues": [],
    }
    return HomeworkEvaluationOut(
        id=row.id,
        attempt_no=row.attempt_no,
        subject_area=row.subject_area,  # type: ignore[arg-type]
        detected_question=row.detected_question,
        student_work_summary=row.student_work_summary,
        extracted_steps=[
            ExtractedStepOut.model_validate(s) for s in (row.extracted_steps_jsonb or [])
        ],
        step_evaluations=[
            StepEvaluationOut.model_validate(s) for s in (row.step_evaluations_jsonb or [])
        ],
        error_classifications=[
            ErrorClassificationOut.model_validate(e)
            for e in (row.error_classifications_jsonb or [])
        ],
        overall_status=row.overall_status,  # type: ignore[arg-type]
        feedback_summary=row.feedback_summary,
        strengths=[str(s) for s in (row.strengths_jsonb or [])],
        unlocked_hints=unlocked_hints,
        current_hint_level_unlocked=unlocked_level,
        max_hint_level=max_level,
        has_more_hints=unlocked_level < max_level,
        solution_revealed=bool(row.solution_revealed),
        complete_solution_markdown=row.complete_solution_markdown if row.solution_revealed else None,
        verifier_results=dict(row.verifier_results_jsonb or {}),
        validation_report=FeedbackValidationReportOut.model_validate(validation_raw),
        revision_recommendations=[
            RevisionRecommendationOut.model_validate(r)
            for r in (row.revision_recommendations_jsonb or [])
        ],
        confidence=round(float(row.confidence), 3),
        confidence_band=row.confidence_band,  # type: ignore[arg-type]
        provider_used=row.provider_used,
        model_id=row.model_id,
        is_fallback=bool(row.is_fallback),
        safety_verdict=row.safety_verdict,
        created_at=row.created_at,
    )


def _persist_evaluation_row(
    db: AsyncSession,
    *,
    submission_id: UUID,
    attempt_no: int,
    draft: EvaluationDraft,
    validation_report: FeedbackValidationReportOut,
) -> HomeworkEvaluation:
    """Create a HomeworkEvaluation ORM record with spoiler_guard defaults enforced."""
    eval_row = HomeworkEvaluation(
        submission_id=submission_id,
        attempt_no=attempt_no,
        subject_area=draft.subject_area,
        detected_question=draft.detected_question,
        student_work_summary=draft.student_work_summary,
        extracted_steps_jsonb=[s.model_dump(mode="json") for s in draft.extracted_steps],
        step_evaluations_jsonb=[s.model_dump(mode="json") for s in draft.step_evaluations],
        error_classifications_jsonb=[e.model_dump(mode="json") for e in draft.error_classifications],
        overall_status=draft.overall_status,
        feedback_summary=draft.feedback_summary,
        strengths_jsonb=list(draft.strengths),
        hints_jsonb=[h.model_dump(mode="json") for h in draft.hints],
        current_hint_level_unlocked=1,
        solution_revealed=False,
        complete_solution_markdown=draft.complete_solution_markdown,
        verifier_results_jsonb=dict(draft.verifier_results),
        validation_report_jsonb=validation_report.model_dump(mode="json"),
        revision_recommendations_jsonb=[
            r.model_dump(mode="json") for r in draft.revision_recommendations
        ],
        confidence=draft.confidence,
        confidence_band=classify_confidence_band(draft.confidence),
        provider_used=draft.provider_used,
        model_id=draft.model_id,
        is_fallback=draft.is_fallback,
        safety_verdict=draft.safety_verdict,
    )
    db.add(eval_row)
    return eval_row


async def _load_submission_detail(
    db: AsyncSession,
    submission: HomeworkSubmission,
) -> HomeworkSubmissionDetailOut:
    files = list(
        (
            await db.scalars(
                select(HomeworkFile)
                .where(HomeworkFile.submission_id == submission.id)
                .order_by(HomeworkFile.page_no.asc())
            )
        ).all()
    )
    ocr_rows = list(
        (
            await db.scalars(
                select(HomeworkOcrResult)
                .where(HomeworkOcrResult.submission_id == submission.id)
                .order_by(HomeworkOcrResult.page_no.asc())
            )
        ).all()
    )
    eval_rows = list(
        (
            await db.scalars(
                select(HomeworkEvaluation)
                .where(HomeworkEvaluation.submission_id == submission.id)
                .order_by(desc(HomeworkEvaluation.attempt_no))
            )
        ).all()
    )
    serialized_evals = [_serialize_evaluation(e) for e in eval_rows]
    return HomeworkSubmissionDetailOut(
        id=submission.id,
        student_id=submission.student_id,
        title=submission.title,
        selected_subject=submission.selected_subject,  # type: ignore[arg-type]
        detected_subject=submission.detected_subject,  # type: ignore[arg-type]
        subject_confidence=submission.subject_confidence,
        language_code=submission.language_code,
        status=submission.status,  # type: ignore[arg-type]
        page_count=submission.page_count,
        retry_count=submission.retry_count,
        needs_ocr_review=submission.needs_ocr_review,
        failure_reason=submission.failure_reason,
        files=[_serialize_file(f) for f in files],
        ocr_pages=[_serialize_ocr_page(o) for o in ocr_rows],
        latest_evaluation=serialized_evals[0] if serialized_evals else None,
        evaluation_history=serialized_evals,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )


async def create_submission_and_evaluate(
    db: AsyncSession,
    *,
    settings: Settings,
    caller: AuthenticatedUser,
    uploaded_files: list[tuple[str | None, str | None, bytes]],
    title: str,
    selected_subject: HomeworkSubjectSelection = "auto",
    language_code: str = "en",
    manual_transcript: str | None = None,
    subject_id: UUID | None = None,
    chapter_id: UUID | None = None,
    concept_id: UUID | None = None,
    ai_gateway: AIRouterGateway | None = None,
) -> HomeworkSubmissionDetailOut:
    """Validate multi-page uploads, store privately, run OCR, and generate subject-aware evaluation."""
    if not uploaded_files:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="NO_FILES_UPLOADED",
            message="Please attach at least one image (JPEG, PNG, WebP) or PDF page.",
        )

    if len(uploaded_files) > settings.homework_max_pages:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MAX_PAGES_EXCEEDED",
            message=f"You can upload at most {settings.homework_max_pages} pages per submission.",
        )

    validated_files: list[ValidatedHomeworkFile] = []
    total_bytes = 0
    total_logical_pages = 0

    for idx, (filename, content_type, raw_bytes) in enumerate(uploaded_files, start=1):
        try:
            vf = validate_and_sanitize_upload(
                filename=filename,
                raw_bytes=raw_bytes,
                declared_content_type=content_type,
                max_file_bytes=settings.homework_max_file_bytes,
                max_pdf_pages=settings.homework_max_pages,
                page_index=idx,
            )
        except FileValidationError as exc:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code=exc.code,
                message=exc.message,
                details={"file_index": idx},
            ) from exc

        total_bytes += vf.size_bytes
        total_logical_pages += vf.pdf_page_count or 1
        if total_bytes > settings.homework_max_total_bytes:
            limit_mb = round(settings.homework_max_total_bytes / (1024 * 1024), 1)
            raise AppError(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                code="TOTAL_UPLOAD_SIZE_EXCEEDED",
                message=f"Combined upload size exceeds the {limit_mb} MB submission limit.",
            )
        if total_logical_pages > settings.homework_max_pages:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="TOTAL_PAGE_LIMIT_EXCEEDED",
                message=(
                    f"Combined document pages ({total_logical_pages}) exceed the maximum "
                    f"allowed {settings.homework_max_pages} pages per submission."
                ),
            )
        validated_files.append(vf)

    clean_title = scrub_pii_text(title.strip())[:200] or "Untitled Homework Submission"
    submission_id = uuid4()
    submission = HomeworkSubmission(
        id=submission_id,
        tenant_id=caller.tenant_id,
        student_id=caller.id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        concept_id=concept_id,
        title=clean_title,
        selected_subject=selected_subject,
        language_code=(language_code or "en").strip()[:16],
        status="ocr_processing",
        page_count=len(validated_files),
        retry_count=0,
        needs_ocr_review=False,
        metadata_jsonb={"logical_page_count": total_logical_pages},
    )
    db.add(submission)
    await db.flush()

    storage = LocalPrivateStorage(settings.storage_local_dir)
    gateway = ai_gateway or AIRouterGateway(settings)
    ocr_pipeline = HomeworkOcrPipeline(settings, ai_gateway=gateway)

    ocr_texts: list[str] = []
    ocr_confidences: list[float] = []
    any_needs_review = False

    for page_no, vf in enumerate(validated_files, start=1):
        storage_key = build_private_homework_storage_key(
            student_id=caller.id,
            submission_id=submission_id,
            page_no=page_no,
            sha256=vf.sha256,
            detected_format=vf.detected_format,
        )
        storage.put_immutable_bytes(storage_key, vf.sanitized_bytes)

        file_row = HomeworkFile(
            submission_id=submission_id,
            page_no=page_no,
            original_filename=vf.original_filename,
            storage_key=storage_key,
            mime_type=vf.mime_type,
            detected_format=vf.detected_format,
            size_bytes=vf.size_bytes,
            sha256=vf.sha256,
            exif_stripped=vf.exif_stripped,
            pdf_page_count=vf.pdf_page_count,
            scan_status=vf.scan_status,
            validation_metadata_jsonb={"warnings": list(vf.warnings)},
        )
        db.add(file_row)
        await db.flush()

        # Pass companion transcript only on page 1 if student typed fallback notes
        page_hint = manual_transcript if page_no == 1 else None
        ocr_outcome = await ocr_pipeline.extract_page(
            raw_bytes=vf.sanitized_bytes,
            detected_format=vf.detected_format,
            mime_type=vf.mime_type,
            page_no=page_no,
            language_code=submission.language_code,
            manual_hint_text=page_hint,
        )
        ocr_row = HomeworkOcrResult(
            submission_id=submission_id,
            file_id=file_row.id,
            page_no=page_no,
            ocr_provider=ocr_outcome.ocr_provider,
            extracted_text=ocr_outcome.extracted_text,
            extracted_latex=ocr_outcome.extracted_latex,
            handwriting_detected=ocr_outcome.handwriting_detected,
            handwriting_supported=ocr_outcome.handwriting_supported,
            confidence=ocr_outcome.confidence,
            needs_review=ocr_outcome.needs_review,
            warnings_jsonb=list(ocr_outcome.warnings),
            raw_jsonb=ocr_outcome.raw_metadata,
        )
        db.add(ocr_row)

        if ocr_outcome.extracted_text.strip():
            ocr_texts.append(ocr_outcome.extracted_text.strip())
        ocr_confidences.append(ocr_outcome.confidence)
        if ocr_outcome.needs_review:
            any_needs_review = True

    combined_text = "\n\n".join(ocr_texts).strip()
    avg_ocr_conf = (
        round(sum(ocr_confidences) / len(ocr_confidences), 3) if ocr_confidences else 0.0
    )

    draft, validation_report, detected_subject, subject_conf = await evaluate_homework_submission(
        combined_text=combined_text,
        selected_subject=selected_subject,
        ocr_avg_confidence=avg_ocr_conf,
        settings=settings,
        is_minor=caller.is_minor,
        ai_gateway=gateway,
    )

    submission.detected_subject = detected_subject
    submission.subject_confidence = subject_conf
    submission.needs_ocr_review = any_needs_review or (
        draft.overall_status == "unreadable_or_uncertain"
    )
    if submission.needs_ocr_review and not combined_text:
        submission.status = "needs_review"
    elif draft.overall_status == "correct":
        submission.status = "completed"
    else:
        submission.status = "feedback_ready"

    _persist_evaluation_row(
        db,
        submission_id=submission_id,
        attempt_no=1,
        draft=draft,
        validation_report=validation_report,
    )

    db.add(
        OutboxEvent(
            tenant_id=caller.tenant_id,
            aggregate_type="homework_submission",
            aggregate_id=str(submission_id),
            topic="HOMEWORK_EVALUATED",
            idempotency_key=f"hw_eval:{submission_id}:attempt:1",
            payload_jsonb={
                "submission_id": str(submission_id),
                "student_id": str(caller.id),
                "subject_area": detected_subject,
                "overall_status": draft.overall_status,
                "error_categories": [e.category for e in draft.error_classifications],
                "attempt_no": 1,
            },
            available_at=datetime.now(UTC),
        )
    )

    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "student",
        action="homework.submission.created",
        resource_type="homework_submission",
        resource_id=str(submission_id),
        tenant_id=caller.tenant_id,
        metadata={
            "page_count": len(validated_files),
            "detected_subject": detected_subject,
            "overall_status": draft.overall_status,
            "needs_ocr_review": submission.needs_ocr_review,
        },
    )

    await emit_in_app_notification(
        db,
        user_id=caller.id,
        tenant_id=caller.tenant_id,
        notification_type="homework_feedback",
        title=(
            f"Review OCR for '{clean_title}'"
            if submission.needs_ocr_review
            else f"Homework feedback ready: {clean_title}"
        ),
        body=(
            "Some handwritten or low-confidence text needs quick confirmation before finalizing feedback."
            if submission.needs_ocr_review
            else f"Step-by-step {detected_subject.replace('_', ' ').title()} evaluation and Hint Level 1 are ready."
        ),
        action_url=f"/homework?submission={submission_id}",
        metadata={"submission_id": str(submission_id), "subject_area": detected_subject},
    )

    await db.commit()
    await db.refresh(submission)
    return await _load_submission_detail(db, submission)


async def list_submissions(
    db: AsyncSession,
    *,
    caller: AuthenticatedUser,
    limit: int = 30,
) -> list[HomeworkSubmissionSummaryOut]:
    """List caller's homework submission history (newest first)."""
    submissions = list(
        (
            await db.scalars(
                select(HomeworkSubmission)
                .where(HomeworkSubmission.student_id == caller.id)
                .order_by(desc(HomeworkSubmission.created_at))
                .limit(max(1, min(limit, 100)))
            )
        ).all()
    )
    if not submissions:
        return []

    sub_ids = [s.id for s in submissions]
    evals = list(
        (
            await db.scalars(
                select(HomeworkEvaluation)
                .where(HomeworkEvaluation.submission_id.in_(sub_ids))
                .order_by(desc(HomeworkEvaluation.attempt_no))
            )
        ).all()
    )
    latest_by_sub: dict[UUID, HomeworkEvaluation] = {}
    for ev in evals:
        if ev.submission_id not in latest_by_sub:
            latest_by_sub[ev.submission_id] = ev

    results: list[HomeworkSubmissionSummaryOut] = []
    for sub in submissions:
        latest = latest_by_sub.get(sub.id)
        results.append(
            HomeworkSubmissionSummaryOut(
                id=sub.id,
                title=sub.title,
                selected_subject=sub.selected_subject,  # type: ignore[arg-type]
                detected_subject=sub.detected_subject,  # type: ignore[arg-type]
                subject_confidence=sub.subject_confidence,
                language_code=sub.language_code,
                status=sub.status,  # type: ignore[arg-type]
                page_count=sub.page_count,
                retry_count=sub.retry_count,
                needs_ocr_review=sub.needs_ocr_review,
                latest_overall_status=latest.overall_status if latest else None,  # type: ignore[arg-type]
                latest_confidence=round(float(latest.confidence), 3) if latest else None,
                error_count=len(latest.error_classifications_jsonb or []) if latest else 0,
                created_at=sub.created_at,
                updated_at=sub.updated_at,
            )
        )
    return results


async def get_submission_detail(
    db: AsyncSession,
    *,
    submission_id: UUID,
    caller: AuthenticatedUser,
) -> HomeworkSubmissionDetailOut:
    """Fetch full submission detail including OCR pages, latest evaluation, and attempt history."""
    submission = _assert_submission_access(
        await db.get(HomeworkSubmission, submission_id),
        caller,
    )
    return await _load_submission_detail(db, submission)


async def get_submission_file_payload(
    db: AsyncSession,
    *,
    settings: Settings,
    submission_id: UUID,
    file_id: UUID,
    caller: AuthenticatedUser,
) -> tuple[bytes, str, str]:
    """Return raw sanitized bytes for an authorized caller from private storage."""
    submission = _assert_submission_access(
        await db.get(HomeworkSubmission, submission_id),
        caller,
    )
    file_row = await db.scalar(
        select(HomeworkFile).where(
            HomeworkFile.id == file_id,
            HomeworkFile.submission_id == submission.id,
        )
    )
    if file_row is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="HOMEWORK_FILE_NOT_FOUND",
            message="Homework file page not found.",
        )

    storage = LocalPrivateStorage(settings.storage_local_dir)
    try:
        data = storage.read_bytes(file_row.storage_key)
    except FileNotFoundError as exc:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="HOMEWORK_FILE_MISSING_IN_STORAGE",
            message="Stored homework file is unavailable.",
        ) from exc

    return data, file_row.mime_type, file_row.original_filename


async def correct_ocr_and_reevaluate(
    db: AsyncSession,
    *,
    settings: Settings,
    submission_id: UUID,
    payload: OcrCorrectionRequest,
    caller: AuthenticatedUser,
    ai_gateway: AIRouterGateway | None = None,
) -> HomeworkSubmissionDetailOut:
    """Save student OCR text corrections, optionally override subject, and re-run evaluation."""
    submission = _assert_submission_access(
        await db.get(HomeworkSubmission, submission_id),
        caller,
        require_owner=True,
    )

    ocr_rows = list(
        (
            await db.scalars(
                select(HomeworkOcrResult)
                .where(HomeworkOcrResult.submission_id == submission.id)
                .order_by(HomeworkOcrResult.page_no.asc())
            )
        ).all()
    )
    by_page = {row.page_no: row for row in ocr_rows}

    for item in payload.pages:
        target = by_page.get(item.page_no)
        if target is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="OCR_PAGE_NOT_FOUND",
                message=f"OCR page {item.page_no} was not found for this submission.",
            )
        target.student_corrected_text = scrub_pii_text(item.corrected_text.strip())
        target.needs_review = False
        target.confidence = max(float(target.confidence), 0.95)

    if payload.subject_override is not None:
        submission.selected_subject = payload.subject_override

    submission.needs_ocr_review = any(r.needs_review for r in ocr_rows)

    if payload.re_evaluate:
        combined_text = "\n\n".join(
            (r.student_corrected_text or r.extracted_text or "").strip()
            for r in ocr_rows
            if (r.student_corrected_text or r.extracted_text or "").strip()
        )
        avg_conf = (
            round(sum(float(r.confidence) for r in ocr_rows) / len(ocr_rows), 3)
            if ocr_rows
            else 0.95
        )
        existing_evals = list(
            (
                await db.scalars(
                    select(HomeworkEvaluation)
                    .where(HomeworkEvaluation.submission_id == submission.id)
                    .order_by(desc(HomeworkEvaluation.attempt_no))
                )
            ).all()
        )
        next_attempt = (existing_evals[0].attempt_no + 1) if existing_evals else 1

        draft, validation_report, detected_subject, subject_conf = (
            await evaluate_homework_submission(
                combined_text=combined_text,
                selected_subject=submission.selected_subject,  # type: ignore[arg-type]
                ocr_avg_confidence=avg_conf,
                settings=settings,
                is_minor=caller.is_minor,
                ai_gateway=ai_gateway,
            )
        )
        submission.detected_subject = detected_subject
        submission.subject_confidence = subject_conf
        submission.status = "completed" if draft.overall_status == "correct" else "feedback_ready"
        _persist_evaluation_row(
            db,
            submission_id=submission.id,
            attempt_no=next_attempt,
            draft=draft,
            validation_report=validation_report,
        )

    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "student",
        action="homework.ocr.corrected",
        resource_type="homework_submission",
        resource_id=str(submission.id),
        tenant_id=caller.tenant_id,
        metadata={
            "pages_updated": [p.page_no for p in payload.pages],
            "re_evaluated": payload.re_evaluate,
        },
    )

    await db.commit()
    await db.refresh(submission)
    return await _load_submission_detail(db, submission)


async def submit_student_retry(
    db: AsyncSession,
    *,
    settings: Settings,
    submission_id: UUID,
    payload: HomeworkRetryRequest,
    caller: AuthenticatedUser,
    ai_gateway: AIRouterGateway | None = None,
) -> HomeworkSubmissionDetailOut:
    """Evaluate a student's revised attempt against the original detected question & prior errors."""
    submission = _assert_submission_access(
        await db.get(HomeworkSubmission, submission_id),
        caller,
        require_owner=True,
    )

    existing_evals = list(
        (
            await db.scalars(
                select(HomeworkEvaluation)
                .where(HomeworkEvaluation.submission_id == submission.id)
                .order_by(desc(HomeworkEvaluation.attempt_no))
            )
        ).all()
    )
    latest_eval = existing_evals[0] if existing_evals else None
    next_attempt = (latest_eval.attempt_no + 1) if latest_eval else 1

    previous_errors = [
        f"{e.get('category', 'error')}: {e.get('summary', '')}"
        for e in (latest_eval.error_classifications_jsonb or [])
    ] if latest_eval else []

    revised_clean = scrub_pii_text(payload.revised_work_text.strip())
    question_prefix = (
        latest_eval.detected_question.strip()
        if latest_eval and latest_eval.detected_question
        else submission.title
    )
    # Keep question line intact if student only typed their revised steps
    if question_prefix.lower() not in revised_clean.lower():
        combined_retry_text = f"Question: {question_prefix}\nSolution:\n{revised_clean}"
    else:
        combined_retry_text = revised_clean

    effective_subject: HomeworkSubjectSelection = (
        submission.detected_subject  # type: ignore[assignment]
        if submission.detected_subject
        else submission.selected_subject  # type: ignore[assignment]
    )

    draft, validation_report, detected_subject, subject_conf = await evaluate_homework_submission(
        combined_text=combined_retry_text,
        selected_subject=effective_subject,
        ocr_avg_confidence=0.98,
        settings=settings,
        is_minor=caller.is_minor,
        ai_gateway=ai_gateway,
        previous_errors=previous_errors,
    )

    # Record progress comparison metadata in verifier_results
    prev_error_count = len(previous_errors)
    curr_error_count = len(draft.error_classifications)
    draft.verifier_results["retry_comparison"] = {
        "previous_attempt_no": latest_eval.attempt_no if latest_eval else 0,
        "previous_error_count": prev_error_count,
        "current_error_count": curr_error_count,
        "errors_resolved": max(0, prev_error_count - curr_error_count),
        "improved": (
            draft.overall_status == "correct"
            or curr_error_count < prev_error_count
        ),
        "student_reflection_present": bool(payload.student_reflection and payload.student_reflection.strip()),
    }

    submission.retry_count += 1
    submission.detected_subject = detected_subject
    submission.subject_confidence = subject_conf
    submission.needs_ocr_review = False
    submission.status = "completed" if draft.overall_status == "correct" else "retry_pending"

    _persist_evaluation_row(
        db,
        submission_id=submission.id,
        attempt_no=next_attempt,
        draft=draft,
        validation_report=validation_report,
    )

    db.add(
        OutboxEvent(
            tenant_id=caller.tenant_id,
            aggregate_type="homework_submission",
            aggregate_id=str(submission.id),
            topic="HOMEWORK_RETRY_EVALUATED",
            idempotency_key=f"hw_retry:{submission.id}:attempt:{next_attempt}",
            payload_jsonb={
                "submission_id": str(submission.id),
                "student_id": str(caller.id),
                "attempt_no": next_attempt,
                "overall_status": draft.overall_status,
                "errors_resolved": max(0, prev_error_count - curr_error_count),
            },
            available_at=datetime.now(UTC),
        )
    )

    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "student",
        action="homework.retry.submitted",
        resource_type="homework_submission",
        resource_id=str(submission.id),
        tenant_id=caller.tenant_id,
        metadata={
            "attempt_no": next_attempt,
            "previous_error_count": prev_error_count,
            "current_error_count": curr_error_count,
            "overall_status": draft.overall_status,
        },
    )

    await db.commit()
    await db.refresh(submission)
    return await _load_submission_detail(db, submission)


async def unlock_next_hint(
    db: AsyncSession,
    *,
    submission_id: UUID,
    target_level: int | None,
    caller: AuthenticatedUser,
) -> HomeworkEvaluationOut:
    """Gradually unlock the next hint level (1 -> 2 -> 3) without spoiling the final solution."""
    submission = _assert_submission_access(
        await db.get(HomeworkSubmission, submission_id),
        caller,
        require_owner=True,
    )
    latest_eval = await db.scalar(
        select(HomeworkEvaluation)
        .where(HomeworkEvaluation.submission_id == submission.id)
        .order_by(desc(HomeworkEvaluation.attempt_no))
        .limit(1)
    )
    if latest_eval is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="HOMEWORK_EVALUATION_NOT_FOUND",
            message="No evaluation exists for this submission yet.",
        )

    desired = (
        target_level
        if target_level is not None
        else min(MAX_HINT_LEVEL, int(latest_eval.current_hint_level_unlocked) + 1)
    )
    # Enforce step-by-step progression: cannot jump more than 1 level ahead of current
    allowed_next = min(MAX_HINT_LEVEL, int(latest_eval.current_hint_level_unlocked) + 1)
    new_level = max(int(latest_eval.current_hint_level_unlocked), min(desired, allowed_next))

    if new_level != latest_eval.current_hint_level_unlocked:
        latest_eval.current_hint_level_unlocked = new_level
        write_audit_log(
            db,
            actor_id=caller.id,
            actor_role=caller.roles[0] if caller.roles else "student",
            action="homework.hint.unlocked",
            resource_type="homework_evaluation",
            resource_id=str(latest_eval.id),
            tenant_id=caller.tenant_id,
            metadata={"submission_id": str(submission.id), "hint_level": new_level},
        )
        await db.commit()
        await db.refresh(latest_eval)

    return _serialize_evaluation(latest_eval)


async def reveal_complete_solution(
    db: AsyncSession,
    *,
    submission_id: UUID,
    confirm_reveal: bool,
    caller: AuthenticatedUser,
) -> HomeworkEvaluationOut:
    """Explicitly unlock the complete solution only when the student confirms reveal."""
    if not confirm_reveal:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="SOLUTION_REVEAL_CONFIRMATION_REQUIRED",
            message="Set confirm_reveal=true to reveal the complete solution after trying hints.",
        )

    submission = _assert_submission_access(
        await db.get(HomeworkSubmission, submission_id),
        caller,
        require_owner=True,
    )
    latest_eval = await db.scalar(
        select(HomeworkEvaluation)
        .where(HomeworkEvaluation.submission_id == submission.id)
        .order_by(desc(HomeworkEvaluation.attempt_no))
        .limit(1)
    )
    if latest_eval is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="HOMEWORK_EVALUATION_NOT_FOUND",
            message="No evaluation exists for this submission yet.",
        )

    if not latest_eval.solution_revealed:
        latest_eval.solution_revealed = True
        latest_eval.current_hint_level_unlocked = MAX_HINT_LEVEL
        write_audit_log(
            db,
            actor_id=caller.id,
            actor_role=caller.roles[0] if caller.roles else "student",
            action="homework.solution.revealed",
            resource_type="homework_evaluation",
            resource_id=str(latest_eval.id),
            tenant_id=caller.tenant_id,
            metadata={"submission_id": str(submission.id), "attempt_no": latest_eval.attempt_no},
        )
        await db.commit()
        await db.refresh(latest_eval)

    return _serialize_evaluation(latest_eval)
