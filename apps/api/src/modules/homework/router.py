"""FastAPI REST endpoints for Phase 6 Homework AI (F-029)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import (
    AuthenticatedUser,
    get_db_session,
    require_any_permission,
    require_permissions,
)
from src.core.config import Settings, get_settings
from src.modules.homework import service
from src.modules.homework.schemas import (
    HomeworkEvaluationOut,
    HomeworkRetryRequest,
    HomeworkSubmissionDetailOut,
    HomeworkSubmissionSummaryOut,
    HomeworkSubjectSelection,
    OcrCorrectionRequest,
    RevealSolutionRequest,
    UnlockHintRequest,
)

homework_router = APIRouter(prefix="/api/v1/homework", tags=["homework"])


def _resolve_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", get_settings())


@homework_router.post(
    "/submissions",
    response_model=HomeworkSubmissionDetailOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_homework_submission(
    request: Request,
    files: Annotated[list[UploadFile], File(description="One or more homework images (JPEG/PNG/WebP) or PDF files")],
    title: Annotated[str, Form(min_length=1, max_length=200)] = "Homework Submission",
    selected_subject: Annotated[HomeworkSubjectSelection, Form()] = "auto",
    language_code: Annotated[str, Form(min_length=2, max_length=16)] = "en",
    manual_transcript: Annotated[str | None, Form(max_length=20000)] = None,
    subject_id: Annotated[UUID | None, Form()] = None,
    chapter_id: Annotated[UUID | None, Form()] = None,
    concept_id: Annotated[UUID | None, Form()] = None,
    caller: AuthenticatedUser = Depends(require_permissions("homework:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> HomeworkSubmissionDetailOut:
    """Upload one or more homework pages, run OCR + subject-aware evaluation, and return Hint Level 1."""
    settings = _resolve_settings(request)
    # Read bounded bytes per uploaded file (+1 byte sentinel so service reports FILE_TOO_LARGE cleanly)
    max_read = settings.homework_max_file_bytes + 1
    uploaded_payloads: list[tuple[str | None, str | None, bytes]] = []
    for upload in files:
        raw = await upload.read(max_read)
        uploaded_payloads.append((upload.filename, upload.content_type, raw))
        await upload.close()

    return await service.create_submission_and_evaluate(
        db,
        settings=settings,
        caller=caller,
        uploaded_files=uploaded_payloads,
        title=title,
        selected_subject=selected_subject,
        language_code=language_code,
        manual_transcript=manual_transcript,
        subject_id=subject_id,
        chapter_id=chapter_id,
        concept_id=concept_id,
    )


@homework_router.get(
    "/submissions",
    response_model=list[HomeworkSubmissionSummaryOut],
)
async def list_homework_submissions(
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    caller: AuthenticatedUser = Depends(require_permissions("homework:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[HomeworkSubmissionSummaryOut]:
    """Return authenticated student's homework submission history."""
    return await service.list_submissions(db, caller=caller, limit=limit)


@homework_router.get(
    "/submissions/{submission_id}",
    response_model=HomeworkSubmissionDetailOut,
)
async def get_homework_submission(
    submission_id: UUID,
    caller: AuthenticatedUser = Depends(  # noqa: B008
        require_any_permission("homework:manage_own", "homework:review")
    ),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> HomeworkSubmissionDetailOut:
    """Return full homework submission detail, OCR pages, evaluation, and attempt history."""
    return await service.get_submission_detail(db, submission_id=submission_id, caller=caller)


@homework_router.get("/submissions/{submission_id}/files/{file_id}")
async def download_homework_file(
    request: Request,
    submission_id: UUID,
    file_id: UUID,
    caller: AuthenticatedUser = Depends(  # noqa: B008
        require_any_permission("homework:manage_own", "homework:review")
    ),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Response:
    """Serve sanitized homework page bytes from private storage to authorized callers only."""
    settings = _resolve_settings(request)
    data, mime_type, filename = await service.get_submission_file_payload(
        db,
        settings=settings,
        submission_id=submission_id,
        file_id=file_id,
        caller=caller,
    )
    safe_disposition = filename.replace('"', "_")
    return Response(
        content=data,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_disposition}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@homework_router.patch(
    "/submissions/{submission_id}/ocr",
    response_model=HomeworkSubmissionDetailOut,
)
async def correct_homework_ocr(
    request: Request,
    submission_id: UUID,
    payload: OcrCorrectionRequest,
    caller: AuthenticatedUser = Depends(require_permissions("homework:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> HomeworkSubmissionDetailOut:
    """Correct low-confidence or misread OCR text and optionally re-run evaluation."""
    settings = _resolve_settings(request)
    return await service.correct_ocr_and_reevaluate(
        db,
        settings=settings,
        submission_id=submission_id,
        payload=payload,
        caller=caller,
    )


@homework_router.post(
    "/submissions/{submission_id}/retry",
    response_model=HomeworkSubmissionDetailOut,
)
async def submit_homework_retry(
    request: Request,
    submission_id: UUID,
    payload: HomeworkRetryRequest,
    caller: AuthenticatedUser = Depends(require_permissions("homework:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> HomeworkSubmissionDetailOut:
    """Submit revised student working steps and compare progress against prior attempt."""
    settings = _resolve_settings(request)
    return await service.submit_student_retry(
        db,
        settings=settings,
        submission_id=submission_id,
        payload=payload,
        caller=caller,
    )


@homework_router.post(
    "/submissions/{submission_id}/hints/unlock",
    response_model=HomeworkEvaluationOut,
)
async def unlock_homework_hint(
    submission_id: UUID,
    payload: UnlockHintRequest,
    caller: AuthenticatedUser = Depends(require_permissions("homework:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> HomeworkEvaluationOut:
    """Unlock the next graduated hint level (Level 1 -> Level 2 -> Level 3)."""
    return await service.unlock_next_hint(
        db,
        submission_id=submission_id,
        target_level=payload.target_level,
        caller=caller,
    )


@homework_router.post(
    "/submissions/{submission_id}/solution/reveal",
    response_model=HomeworkEvaluationOut,
)
async def reveal_homework_solution(
    submission_id: UUID,
    payload: RevealSolutionRequest,
    caller: AuthenticatedUser = Depends(require_permissions("homework:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> HomeworkEvaluationOut:
    """Explicitly reveal the complete solution once the student confirms."""
    return await service.reveal_complete_solution(
        db,
        submission_id=submission_id,
        confirm_reveal=payload.confirm_reveal,
        caller=caller,
    )
