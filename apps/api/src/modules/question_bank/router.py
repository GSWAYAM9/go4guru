"""API routers for Canonical Question Bank and Excel/CSV Staging Importer."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import (
    AuthenticatedUser,
    get_db_session,
    require_any_permission,
    require_permissions,
)
from src.core.config import Settings, get_settings
from src.core.errors import AppError
from src.modules.question_bank.importer import serialize_import_report_csv
from src.modules.question_bank.models import ImportBatch, ImportStagingRow
from src.modules.question_bank.schemas import (
    ColumnMappingRequest,
    ImportBatchOut,
    ImportCommitRequest,
    ImportCommitResponse,
    ImportPreviewResponse,
    ImportRollbackResponse,
    QuestionCreateRequest,
    QuestionNewVersionRequest,
    QuestionOut,
    QuestionReviewRequest,
    QuestionSearchResponse,
    VerifyPyqRequest,
)
from src.modules.question_bank.service import QuestionBankService

questions_router = APIRouter(prefix="/api/v1/questions", tags=["questions"])
imports_router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


_READ_QUESTION_DEP = require_any_permission("question:read_redacted", "question:read_full")


@questions_router.get("", response_model=QuestionSearchResponse)
async def search_questions(
    request: Request,
    q: str | None = None,
    grade_id: UUID | None = None,
    subject_id: UUID | None = None,
    chapter_id: UUID | None = None,
    topic_id: UUID | None = None,
    concept_id: UUID | None = None,
    question_type: str | None = None,
    difficulty: str | None = None,
    is_pyq: bool | None = None,
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
    caller: AuthenticatedUser = Depends(_READ_QUESTION_DEP),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> QuestionSearchResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).search_questions(
        caller=caller,
        q_text=q,
        grade_id=grade_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        topic_id=topic_id,
        concept_id=concept_id,
        question_type=question_type,
        difficulty=difficulty,
        is_pyq=is_pyq,
        status_filter=status_filter,
        limit=max(1, min(limit, 100)),
        offset=max(0, offset),
    )


@questions_router.get("/{question_id}", response_model=QuestionOut)
async def get_question(
    question_id: UUID,
    request: Request,
    caller: AuthenticatedUser = Depends(_READ_QUESTION_DEP),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> QuestionOut:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).get_question(question_id, caller)


@questions_router.post("", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(
    payload: QuestionCreateRequest,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("question:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> QuestionOut:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).create_question(payload, caller)


@questions_router.post(
    "/{question_id}/versions",
    response_model=QuestionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_question_version(
    question_id: UUID,
    payload: QuestionNewVersionRequest,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("question:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> QuestionOut:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).create_new_version(question_id, payload, caller)


@questions_router.post("/{question_id}/review", response_model=QuestionOut)
async def review_question(
    question_id: UUID,
    payload: QuestionReviewRequest,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("question:review")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> QuestionOut:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).review_question(question_id, payload, caller)


@questions_router.post("/{question_id}/verify-pyq", response_model=QuestionOut)
async def verify_question_pyq(
    question_id: UUID,
    payload: VerifyPyqRequest,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("question:review")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> QuestionOut:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).verify_pyq(question_id, payload, caller)


@imports_router.get("", response_model=list[ImportBatchOut])
async def list_import_batches(
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("import:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[ImportBatchOut]:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    svc = QuestionBankService(db, settings)
    batches = list(
        (
            await db.scalars(select(ImportBatch).order_by(ImportBatch.created_at.desc()).limit(50))
        ).all()
    )
    return [svc._batch_to_out(b) for b in batches]


@imports_router.post("/upload", response_model=ImportBatchOut, status_code=status.HTTP_201_CREATED)
async def upload_import_workbook(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("import:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ImportBatchOut:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    data = await file.read()
    return await QuestionBankService(db, settings).upload_import_file(
        filename=file.filename or "upload.xlsx",
        file_bytes=data,
        caller=caller,
    )


@imports_router.post("/{batch_id}/mapping", response_model=ImportBatchOut)
async def save_import_mapping(
    batch_id: UUID,
    payload: ColumnMappingRequest,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("import:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ImportBatchOut:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).save_mapping(batch_id, payload, caller)


@imports_router.post("/{batch_id}/validate", response_model=ImportBatchOut)
async def validate_import_batch(
    batch_id: UUID,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("import:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ImportBatchOut:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).validate_batch(batch_id, caller)


@imports_router.get("/{batch_id}/preview", response_model=ImportPreviewResponse)
async def preview_import_batch(
    batch_id: UUID,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("import:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ImportPreviewResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).get_preview(batch_id)


@imports_router.post("/{batch_id}/commit", response_model=ImportCommitResponse)
async def commit_import_batch(
    batch_id: UUID,
    payload: ImportCommitRequest,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("import:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ImportCommitResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).commit_batch(batch_id, payload, caller)


@imports_router.post("/{batch_id}/rollback", response_model=ImportRollbackResponse)
async def rollback_import_batch(
    batch_id: UUID,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("import:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ImportRollbackResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await QuestionBankService(db, settings).rollback_batch(batch_id, caller)


@imports_router.get("/{batch_id}/report")
async def download_import_report(
    batch_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("import:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Response:
    batch = await db.get(ImportBatch, batch_id)
    if batch is None:
        raise AppError(status_code=404, code="BATCH_NOT_FOUND", message="Import batch missing.")
    rows = list(
        (
            await db.scalars(
                select(ImportStagingRow)
                .where(ImportStagingRow.import_batch_id == batch.id)
                .order_by(ImportStagingRow.row_number)
            )
        ).all()
    )
    csv_body = serialize_import_report_csv(
        [
            {
                "row_number": r.row_number,
                "sheet_name": r.sheet_name,
                "validation_status": r.validation_status,
                "errors": r.errors_jsonb,
                "warnings": r.warnings_jsonb,
                "created_question_id": r.created_question_id,
            }
            for r in rows
        ]
    )
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="import-report-{batch.id}.csv"'},
    )
