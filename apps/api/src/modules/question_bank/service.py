"""Service layer for Question Bank CRUD, versioning, PYQ provenance, and Excel imports."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.config import Settings
from src.core.errors import AppError
from src.core.storage import LocalPrivateStorage
from src.modules.content.public import assert_license_usable
from src.modules.curriculum.public import resolve_hierarchy_by_names
from src.modules.question_bank.importer import (
    compute_canonical_hash,
    inspect_and_parse_workbook,
    map_and_validate_row,
)
from src.modules.question_bank.models import (
    ImportBatch,
    ImportStagingRow,
    Question,
    QuestionHint,
    QuestionOption,
    QuestionProvenance,
    QuestionReview,
    QuestionSolution,
    QuestionVersion,
)
from src.modules.question_bank.schemas import (
    ColumnMappingRequest,
    DetectedSheetInfo,
    ImportBatchOut,
    ImportCommitRequest,
    ImportCommitResponse,
    ImportPreviewResponse,
    ImportRollbackResponse,
    OptionOut,
    ProvenanceOut,
    QuestionCreateRequest,
    QuestionNewVersionRequest,
    QuestionOut,
    QuestionReviewRequest,
    QuestionSearchResponse,
    SolutionOut,
    StagingRowOut,
    VerifyPyqRequest,
)


class QuestionBankService:
    """Manages canonical questions, immutable versions, rights, and Excel import stages."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def _serialize_question(
        self,
        q: Question,
        qv: QuestionVersion,
        *,
        include_answers: bool,
    ) -> QuestionOut:
        options = list(
            (
                await self.db.scalars(
                    select(QuestionOption)
                    .where(QuestionOption.question_version_id == qv.id)
                    .order_by(QuestionOption.option_key)
                )
            ).all()
        )
        hints_count = int(
            await self.db.scalar(
                select(func.count(QuestionHint.id)).where(QuestionHint.question_version_id == qv.id)
            )
            or 0
        )
        prov = await self.db.get(QuestionProvenance, q.id)
        solutions_out: list[SolutionOut] | None = None
        if include_answers:
            sol_rows = list(
                (
                    await self.db.scalars(
                        select(QuestionSolution).where(
                            QuestionSolution.question_version_id == qv.id
                        )
                    )
                ).all()
            )
            solutions_out = [
                SolutionOut(
                    language_code=s.language_code,
                    solution_type=s.solution_type,
                    explanation_markdown=s.explanation_markdown,
                    steps=list(s.steps_jsonb),
                    common_mistakes_markdown=s.common_mistakes_markdown,
                )
                for s in sol_rows
            ]

        return QuestionOut(
            id=q.id,
            version_id=qv.id,
            version_no=qv.version_no,
            status=q.status,
            question_type=q.question_type,
            language_code=qv.language_code,
            curriculum_version_id=qv.curriculum_version_id,
            grade_id=qv.grade_id,
            subject_id=qv.subject_id,
            chapter_id=qv.chapter_id,
            topic_id=qv.topic_id,
            concept_id=qv.concept_id,
            stem_markdown=qv.stem_markdown,
            passage_markdown=qv.passage_markdown,
            difficulty=qv.difficulty,
            default_marks=float(qv.default_marks),
            default_negative_marks=float(qv.default_negative_marks),
            estimated_seconds=qv.estimated_seconds,
            ai_generated=qv.ai_generated,
            options=[
                OptionOut(
                    option_key=o.option_key,
                    content_markdown=o.content_markdown,
                    is_correct=o.is_correct if include_answers else None,
                    match_pair_key=o.match_pair_key,
                )
                for o in options
            ],
            hints_available_count=hints_count,
            provenance=(
                ProvenanceOut(
                    source_id=prov.source_id,
                    license_id=prov.license_id,
                    source_type=prov.source_type,
                    is_pyq=prov.is_pyq,
                    exam_name=prov.exam_name,
                    exam_year=prov.exam_year,
                    exam_session=prov.exam_session,
                    verification_status=prov.verification_status,
                )
                if prov
                else None
            ),
            correct_answer_jsonb=qv.correct_answer_jsonb if include_answers else None,
            solutions=solutions_out,
        )

    async def create_question(
        self, payload: QuestionCreateRequest, caller: AuthenticatedUser
    ) -> QuestionOut:
        await assert_license_usable(
            self.db,
            source_id=payload.provenance.source_id,
            license_id=payload.provenance.license_id,
            require_approved=False,
        )
        if payload.provenance.is_pyq or payload.provenance.source_type == "verified_pyq":
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="PYQ_REQUIRES_VERIFICATION_FLOW",
                message=(
                    "New questions cannot start as verified PYQs; "
                    "create as unverified and use /verify-pyq after reviewer sign-off."
                ),
            )
        if payload.ai_generated and payload.provenance.source_type != "ai_generated":
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="AI_PROVENANCE_MISMATCH",
                message="ai_generated=true requires source_type='ai_generated'.",
            )

        canonical_hash = compute_canonical_hash(payload.stem_markdown, payload.question_type)
        q = Question(
            canonical_hash=canonical_hash,
            question_type=payload.question_type,
            status="DRAFT",
            created_by=caller.id,
        )
        self.db.add(q)
        await self.db.flush()

        qv = QuestionVersion(
            question_id=q.id,
            version_no=1,
            language_code=payload.language_code,
            curriculum_version_id=payload.curriculum_version_id,
            grade_id=payload.grade_id,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
            learning_objective_id=payload.learning_objective_id,
            stem_markdown=payload.stem_markdown,
            passage_markdown=payload.passage_markdown,
            answer_schema_jsonb=payload.answer_schema_jsonb,
            correct_answer_jsonb=payload.correct_answer_jsonb,
            difficulty=payload.difficulty,
            default_marks=Decimal(str(payload.default_marks)),
            default_negative_marks=Decimal(str(payload.default_negative_marks)),
            estimated_seconds=payload.estimated_seconds,
            cognitive_level=payload.cognitive_level,
            competency_tag=payload.competency_tag,
            ai_generated=payload.ai_generated,
            ai_metadata_jsonb=payload.ai_metadata_jsonb,
        )
        self.db.add(qv)
        await self.db.flush()
        q.current_version_id = qv.id

        for opt in payload.options:
            self.db.add(
                QuestionOption(
                    question_version_id=qv.id,
                    option_key=opt.option_key.upper(),
                    content_markdown=opt.content_markdown,
                    is_correct=opt.is_correct,
                    match_pair_key=opt.match_pair_key,
                )
            )
        for sol in payload.solutions:
            self.db.add(
                QuestionSolution(
                    question_version_id=qv.id,
                    language_code=sol.language_code,
                    solution_type=sol.solution_type,
                    explanation_markdown=sol.explanation_markdown,
                    steps_jsonb=sol.steps,
                    common_mistakes_markdown=sol.common_mistakes_markdown,
                    misconception_tags_jsonb=sol.misconception_tags,
                    rubric_jsonb=sol.rubric,
                )
            )
        for hint in payload.hints:
            self.db.add(
                QuestionHint(
                    question_version_id=qv.id,
                    hint_level=hint.hint_level,
                    hint_markdown=hint.hint_markdown,
                )
            )
        self.db.add(
            QuestionProvenance(
                question_id=q.id,
                source_id=payload.provenance.source_id,
                license_id=payload.provenance.license_id,
                source_type=payload.provenance.source_type,
                is_pyq=False,
                exam_name=payload.provenance.exam_name,
                exam_year=payload.provenance.exam_year,
                exam_session=payload.provenance.exam_session,
                exam_shift=payload.provenance.exam_shift,
                paper_code=payload.provenance.paper_code,
                question_number=payload.provenance.question_number,
                source_url=payload.provenance.source_url,
                verification_status="unverified",
            )
        )
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="question.created",
            resource_type="question",
            resource_id=str(q.id),
            metadata={"version_no": 1, "question_type": payload.question_type},
        )
        await self.db.commit()
        return await self._serialize_question(q, qv, include_answers=True)

    async def create_new_version(
        self, question_id: UUID, payload: QuestionNewVersionRequest, caller: AuthenticatedUser
    ) -> QuestionOut:
        q = await self.db.get(Question, question_id)
        if q is None or q.deleted_at is not None:
            raise AppError(
                status_code=404, code="QUESTION_NOT_FOUND", message="Question not found."
            )

        latest_no = int(
            await self.db.scalar(
                select(func.max(QuestionVersion.version_no)).where(
                    QuestionVersion.question_id == q.id
                )
            )
            or 0
        )
        next_no = latest_no + 1
        prev_qv = (
            await self.db.get(QuestionVersion, q.current_version_id)
            if q.current_version_id
            else None
        )
        qv = QuestionVersion(
            question_id=q.id,
            version_no=next_no,
            language_code=payload.language_code,
            curriculum_version_id=payload.curriculum_version_id,
            grade_id=payload.grade_id,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
            learning_objective_id=payload.learning_objective_id,
            stem_markdown=payload.stem_markdown,
            passage_markdown=payload.passage_markdown,
            answer_schema_jsonb=payload.answer_schema_jsonb,
            correct_answer_jsonb=payload.correct_answer_jsonb,
            difficulty=payload.difficulty,
            default_marks=Decimal(str(payload.default_marks)),
            default_negative_marks=Decimal(str(payload.default_negative_marks)),
            estimated_seconds=payload.estimated_seconds,
            ai_generated=prev_qv.ai_generated if prev_qv else False,
            ai_metadata_jsonb=prev_qv.ai_metadata_jsonb if prev_qv else {},
        )
        self.db.add(qv)
        await self.db.flush()
        q.current_version_id = qv.id
        q.canonical_hash = compute_canonical_hash(payload.stem_markdown, q.question_type)
        q.status = "REVIEW"

        for opt in payload.options:
            self.db.add(
                QuestionOption(
                    question_version_id=qv.id,
                    option_key=opt.option_key.upper(),
                    content_markdown=opt.content_markdown,
                    is_correct=opt.is_correct,
                    match_pair_key=opt.match_pair_key,
                )
            )
        for sol in payload.solutions:
            self.db.add(
                QuestionSolution(
                    question_version_id=qv.id,
                    language_code=sol.language_code,
                    solution_type=sol.solution_type,
                    explanation_markdown=sol.explanation_markdown,
                    steps_jsonb=sol.steps,
                    common_mistakes_markdown=sol.common_mistakes_markdown,
                    misconception_tags_jsonb=sol.misconception_tags,
                    rubric_jsonb=sol.rubric,
                )
            )
        for hint in payload.hints:
            self.db.add(
                QuestionHint(
                    question_version_id=qv.id,
                    hint_level=hint.hint_level,
                    hint_markdown=hint.hint_markdown,
                )
            )
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="question.version_created",
            resource_type="question",
            resource_id=str(q.id),
            metadata={"version_no": next_no, "version_id": str(qv.id)},
        )
        await self.db.commit()
        return await self._serialize_question(q, qv, include_answers=True)

    async def review_question(
        self, question_id: UUID, payload: QuestionReviewRequest, caller: AuthenticatedUser
    ) -> QuestionOut:
        q = await self.db.get(Question, question_id)
        if q is None or q.current_version_id is None or q.deleted_at is not None:
            raise AppError(
                status_code=404, code="QUESTION_NOT_FOUND", message="Question not found."
            )
        qv = await self.db.get(QuestionVersion, q.current_version_id)
        assert qv is not None

        if payload.publish:
            if not caller.has_permission("question:publish"):
                raise AppError(
                    status_code=403,
                    code="FORBIDDEN",
                    message="Publishing requires question:publish permission.",
                )
            if payload.decision != "approved":
                raise AppError(
                    status_code=422,
                    code="PUBLISH_REQUIRES_APPROVAL",
                    message="Cannot publish when review decision is not approved.",
                )
            prov = await self.db.get(QuestionProvenance, q.id)
            if prov is None:
                raise AppError(
                    status_code=422,
                    code="PROVENANCE_REQUIRED",
                    message="Provenance is required before publishing.",
                )
            await assert_license_usable(
                self.db,
                source_id=prov.source_id,
                license_id=prov.license_id,
                require_approved=True,
            )

        self.db.add(
            QuestionReview(
                question_version_id=qv.id,
                reviewer_id=caller.id,
                decision=payload.decision,
                feedback=payload.feedback,
            )
        )
        if payload.decision == "approved":
            q.status = "PUBLISHED" if payload.publish else "APPROVED"
        elif payload.decision == "rejected":
            q.status = "ARCHIVED"
        else:
            q.status = "DRAFT"

        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="question.reviewed",
            resource_type="question",
            resource_id=str(q.id),
            metadata={"decision": payload.decision, "status": q.status},
        )
        await self.db.commit()
        return await self._serialize_question(q, qv, include_answers=True)

    async def verify_pyq(
        self, question_id: UUID, payload: VerifyPyqRequest, caller: AuthenticatedUser
    ) -> QuestionOut:
        q = await self.db.get(Question, question_id)
        if q is None or q.current_version_id is None or q.deleted_at is not None:
            raise AppError(
                status_code=404, code="QUESTION_NOT_FOUND", message="Question not found."
            )
        qv = await self.db.get(QuestionVersion, q.current_version_id)
        assert qv is not None
        if qv.ai_generated:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="AI_QUESTION_CANNOT_BE_PYQ",
                message="AI-generated questions must never be marked as verified PYQs.",
            )
        prov = await self.db.get(QuestionProvenance, q.id)
        if prov is None:
            raise AppError(
                status_code=422, code="PROVENANCE_MISSING", message="Missing provenance."
            )

        prov.is_pyq = True
        prov.source_type = "verified_pyq"
        prov.exam_name = payload.exam_name
        prov.exam_year = payload.exam_year
        prov.exam_session = payload.exam_session
        prov.exam_shift = payload.exam_shift
        prov.paper_code = payload.paper_code
        prov.question_number = payload.question_number
        prov.source_url = payload.source_url
        prov.verification_status = "verified"
        prov.verified_by = caller.id
        prov.verified_at = datetime.now(UTC)

        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="question.pyq_verified",
            resource_type="question",
            resource_id=str(q.id),
            metadata={"exam_name": payload.exam_name, "exam_year": payload.exam_year},
        )
        await self.db.commit()
        return await self._serialize_question(q, qv, include_answers=True)

    async def search_questions(
        self,
        *,
        caller: AuthenticatedUser,
        q_text: str | None = None,
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
    ) -> QuestionSearchResponse:
        can_read_full = caller.has_permission("question:read_full") and (
            not caller.requires_mfa or caller.mfa_verified
        )

        stmt = (
            select(Question, QuestionVersion)
            .join(QuestionVersion, Question.current_version_id == QuestionVersion.id)
            .where(Question.deleted_at.is_(None))
        )
        if not can_read_full:
            stmt = stmt.where(Question.status == "PUBLISHED")
        elif status_filter:
            stmt = stmt.where(Question.status == status_filter)

        if q_text:
            stmt = stmt.where(QuestionVersion.stem_markdown.ilike(f"%{q_text.strip()}%"))
        if grade_id:
            stmt = stmt.where(QuestionVersion.grade_id == grade_id)
        if subject_id:
            stmt = stmt.where(QuestionVersion.subject_id == subject_id)
        if chapter_id:
            stmt = stmt.where(QuestionVersion.chapter_id == chapter_id)
        if topic_id:
            stmt = stmt.where(QuestionVersion.topic_id == topic_id)
        if concept_id:
            stmt = stmt.where(QuestionVersion.concept_id == concept_id)
        if question_type:
            stmt = stmt.where(Question.question_type == question_type)
        if difficulty:
            stmt = stmt.where(QuestionVersion.difficulty == difficulty)
        if is_pyq is not None:
            stmt = stmt.join(
                QuestionProvenance, QuestionProvenance.question_id == Question.id
            ).where(QuestionProvenance.is_pyq == is_pyq)

        all_rows = (await self.db.execute(stmt.order_by(Question.created_at.desc()))).all()
        total = len(all_rows)
        paged = all_rows[offset : offset + limit]
        items = [
            await self._serialize_question(q, qv, include_answers=can_read_full) for q, qv in paged
        ]
        return QuestionSearchResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_question(self, question_id: UUID, caller: AuthenticatedUser) -> QuestionOut:
        can_read_full = caller.has_permission("question:read_full") and (
            not caller.requires_mfa or caller.mfa_verified
        )
        q = await self.db.get(Question, question_id)
        if q is None or q.current_version_id is None or q.deleted_at is not None:
            raise AppError(
                status_code=404, code="QUESTION_NOT_FOUND", message="Question not found."
            )
        if not can_read_full and q.status != "PUBLISHED":
            raise AppError(
                status_code=404, code="QUESTION_NOT_FOUND", message="Question not found."
            )
        qv = await self.db.get(QuestionVersion, q.current_version_id)
        assert qv is not None
        return await self._serialize_question(q, qv, include_answers=can_read_full)

    # ------------------------------------------------------------------
    # Excel / CSV 14-Stage Pipeline Methods
    # ------------------------------------------------------------------
    def _batch_to_out(
        self, batch: ImportBatch, duplicate_warning: str | None = None
    ) -> ImportBatchOut:
        return ImportBatchOut(
            id=batch.id,
            original_filename=batch.original_filename,
            file_format=batch.file_format,
            file_sha256=batch.file_sha256,
            status=batch.status,
            selected_sheet=batch.selected_sheet,
            detected_sheets=[DetectedSheetInfo(**s) for s in batch.detected_sheets_jsonb],
            column_mapping=batch.column_mapping_jsonb,
            total_rows=batch.total_rows,
            valid_rows=batch.valid_rows,
            warning_rows=batch.warning_rows,
            error_rows=batch.error_rows,
            duplicate_rows=batch.duplicate_rows,
            duplicate_file_warning=duplicate_warning,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
        )

    async def upload_import_file(
        self,
        *,
        filename: str,
        file_bytes: bytes,
        caller: AuthenticatedUser,
    ) -> ImportBatchOut:
        if len(file_bytes) == 0:
            raise AppError(status_code=422, code="EMPTY_FILE", message="Uploaded file is empty.")
        if len(file_bytes) > self.settings.max_import_file_bytes:
            raise AppError(
                status_code=413,
                code="FILE_TOO_LARGE",
                message="File exceeds maximum allowed import size.",
            )
        lower_name = filename.lower()
        file_format: Literal["xlsx", "csv"]
        if lower_name.endswith(".xlsx"):
            file_format = "xlsx"
        elif lower_name.endswith(".csv"):
            file_format = "csv"
        else:
            raise AppError(
                status_code=422,
                code="UNSUPPORTED_FILE_FORMAT",
                message="Only .xlsx and .csv workbooks are supported.",
            )

        try:
            sheets_meta, rows_by_sheet = inspect_and_parse_workbook(file_bytes, file_format)
        except ValueError as exc:
            raise AppError(status_code=422, code="MALFORMED_WORKBOOK", message=str(exc)) from exc

        file_sha = hashlib.sha256(file_bytes).hexdigest()
        prior_batch = await self.db.scalar(
            select(ImportBatch).where(ImportBatch.file_sha256 == file_sha)
        )
        dup_warning = (
            f"Identical file SHA-256 already uploaded in batch {prior_batch.id}."
            if prior_batch is not None
            else None
        )

        batch_id = uuid4()
        storage_key = f"imports/raw/{batch_id}/{file_sha}.{file_format}"
        LocalPrivateStorage(self.settings.storage_local_dir).put_immutable_bytes(
            storage_key, file_bytes
        )

        default_sheet = sheets_meta[0]["sheet_name"] if sheets_meta else None
        total_rows = sum(len(v) for v in rows_by_sheet.values())
        batch = ImportBatch(
            id=batch_id,
            uploaded_by=caller.id,
            tenant_id=caller.tenant_id,
            original_filename=filename[:256],
            file_format=file_format,
            file_sha256=file_sha,
            storage_key=storage_key,
            status="uploaded",
            detected_sheets_jsonb=sheets_meta,
            selected_sheet=default_sheet,
            total_rows=total_rows,
        )
        self.db.add(batch)
        await self.db.flush()

        for s_name, row_items in rows_by_sheet.items():
            for item in row_items:
                self.db.add(
                    ImportStagingRow(
                        import_batch_id=batch.id,
                        sheet_name=s_name,
                        row_number=item["row_number"],
                        raw_payload_jsonb=item["raw"],
                        validation_status="pending",
                    )
                )

        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="import.uploaded",
            resource_type="import_batch",
            resource_id=str(batch.id),
            metadata={"filename": filename, "sha256": file_sha, "total_rows": total_rows},
        )
        await self.db.commit()
        await self.db.refresh(batch)
        return self._batch_to_out(batch, dup_warning)

    async def save_mapping(
        self, batch_id: UUID, payload: ColumnMappingRequest, caller: AuthenticatedUser
    ) -> ImportBatchOut:
        batch = await self.db.get(ImportBatch, batch_id)
        if batch is None:
            raise AppError(status_code=404, code="BATCH_NOT_FOUND", message="Import batch missing.")
        sheet_names = {s["sheet_name"] for s in batch.detected_sheets_jsonb}
        if payload.selected_sheet not in sheet_names:
            raise AppError(
                status_code=422,
                code="INVALID_SHEET",
                message=f"Sheet '{payload.selected_sheet}' does not exist in uploaded workbook.",
            )
        await assert_license_usable(
            self.db,
            source_id=payload.source_id,
            license_id=payload.license_id,
            require_approved=False,
        )

        batch.selected_sheet = payload.selected_sheet
        batch.column_mapping_jsonb = {
            "column_map": payload.column_map,
            "default_curriculum_version_id": str(payload.default_curriculum_version_id),
            "default_grade_id": str(payload.default_grade_id),
            "default_subject_id": str(payload.default_subject_id),
            "default_chapter_id": str(payload.default_chapter_id),
            "default_topic_id": str(payload.default_topic_id) if payload.default_topic_id else None,
            "default_concept_id": (
                str(payload.default_concept_id) if payload.default_concept_id else None
            ),
            "source_id": str(payload.source_id),
            "license_id": str(payload.license_id),
        }
        batch.status = "mapped"
        await self.db.commit()
        await self.db.refresh(batch)
        return self._batch_to_out(batch)

    async def validate_batch(self, batch_id: UUID, caller: AuthenticatedUser) -> ImportBatchOut:
        batch = await self.db.get(ImportBatch, batch_id)
        if batch is None:
            raise AppError(status_code=404, code="BATCH_NOT_FOUND", message="Import batch missing.")
        mapping_cfg = batch.column_mapping_jsonb
        column_map: dict[str, str] = mapping_cfg.get("column_map", {})
        if not column_map or not batch.selected_sheet:
            raise AppError(
                status_code=422,
                code="MAPPING_REQUIRED",
                message="Configure sheet and column mapping before validation.",
            )

        staging_rows = list(
            (
                await self.db.scalars(
                    select(ImportStagingRow)
                    .where(
                        ImportStagingRow.import_batch_id == batch.id,
                        ImportStagingRow.sheet_name == batch.selected_sheet,
                    )
                    .order_by(ImportStagingRow.row_number)
                )
            ).all()
        )
        existing_hashes = set(
            (
                await self.db.scalars(
                    select(Question.canonical_hash).where(Question.deleted_at.is_(None))
                )
            ).all()
        )
        seen_in_batch: set[str] = set()

        valid_count = 0
        warning_count = 0
        error_count = 0
        duplicate_count = 0

        for row in staging_rows:
            norm, errors, warnings = map_and_validate_row(
                raw_row=row.raw_payload_jsonb, column_map=column_map
            )
            c_hash = norm["canonical_hash"]

            # Academic mapping resolution if row overrides default chapter/grade/subject
            grade_num = None
            if norm.get("grade"):
                try:
                    grade_num = int("".join(ch for ch in str(norm["grade"]) if ch.isdigit()))
                except ValueError:
                    grade_num = None

            resolved_cv = mapping_cfg["default_curriculum_version_id"]
            resolved_grade = mapping_cfg["default_grade_id"]
            resolved_subject = mapping_cfg["default_subject_id"]
            resolved_chapter = mapping_cfg["default_chapter_id"]
            resolved_topic = mapping_cfg.get("default_topic_id")
            resolved_concept = mapping_cfg.get("default_concept_id")

            if norm.get("chapter"):
                ctx = await resolve_hierarchy_by_names(
                    self.db,
                    grade_number=grade_num,
                    subject_name_or_code=norm.get("subject"),
                    chapter_title_or_code=norm.get("chapter"),
                    topic_title=norm.get("topic"),
                    concept_code=norm.get("concept_code"),
                )
                if ctx is not None:
                    resolved_cv = str(ctx.curriculum_version_id)
                    resolved_grade = str(ctx.grade_id)
                    resolved_subject = str(ctx.subject_id)
                    resolved_chapter = str(ctx.chapter_id)
                    if ctx.topic_id:
                        resolved_topic = str(ctx.topic_id)
                    if ctx.concept_id:
                        resolved_concept = str(ctx.concept_id)
                else:
                    warnings.append(
                        f"Could not match chapter '{norm['chapter']}' by name; "
                        "falling back to batch default curriculum."
                    )

            norm["resolved_curriculum_version_id"] = resolved_cv
            norm["resolved_grade_id"] = resolved_grade
            norm["resolved_subject_id"] = resolved_subject
            norm["resolved_chapter_id"] = resolved_chapter
            norm["resolved_topic_id"] = resolved_topic
            norm["resolved_concept_id"] = resolved_concept

            is_duplicate = False
            if c_hash in existing_hashes:
                is_duplicate = True
                warnings.append("Exact canonical question already exists in Question Bank.")
            elif c_hash in seen_in_batch:
                is_duplicate = True
                warnings.append("Duplicate question detected earlier in this batch.")
            seen_in_batch.add(c_hash)

            row.normalized_payload_jsonb = norm
            row.row_fingerprint_sha256 = c_hash
            row.errors_jsonb = errors
            row.warnings_jsonb = warnings

            if errors:
                row.validation_status = "error"
                error_count += 1
            elif is_duplicate:
                row.validation_status = "duplicate"
                duplicate_count += 1
            elif warnings:
                row.validation_status = "warning"
                warning_count += 1
            else:
                row.validation_status = "valid"
                valid_count += 1

        batch.total_rows = len(staging_rows)
        batch.valid_rows = valid_count
        batch.warning_rows = warning_count
        batch.error_rows = error_count
        batch.duplicate_rows = duplicate_count
        batch.status = "preview_ready"
        await self.db.commit()
        await self.db.refresh(batch)
        return self._batch_to_out(batch)

    async def get_preview(self, batch_id: UUID) -> ImportPreviewResponse:
        batch = await self.db.get(ImportBatch, batch_id)
        if batch is None:
            raise AppError(status_code=404, code="BATCH_NOT_FOUND", message="Import batch missing.")
        rows = list(
            (
                await self.db.scalars(
                    select(ImportStagingRow)
                    .where(ImportStagingRow.import_batch_id == batch.id)
                    .order_by(ImportStagingRow.row_number)
                    .limit(200)
                )
            ).all()
        )
        return ImportPreviewResponse(
            batch=self._batch_to_out(batch),
            rows=[
                StagingRowOut(
                    id=r.id,
                    sheet_name=r.sheet_name,
                    row_number=r.row_number,
                    validation_status=r.validation_status,
                    raw_payload=r.raw_payload_jsonb,
                    normalized_payload=r.normalized_payload_jsonb,
                    errors=list(r.errors_jsonb),
                    warnings=list(r.warnings_jsonb),
                    created_question_id=r.created_question_id,
                )
                for r in rows
            ],
        )

    async def commit_batch(
        self, batch_id: UUID, payload: ImportCommitRequest, caller: AuthenticatedUser
    ) -> ImportCommitResponse:
        batch = await self.db.get(ImportBatch, batch_id)
        if batch is None:
            raise AppError(status_code=404, code="BATCH_NOT_FOUND", message="Import batch missing.")
        if batch.status == "committed":
            # Idempotent replay
            return ImportCommitResponse(
                batch_id=batch.id,
                committed_count=0,
                skipped_count=batch.error_rows + batch.duplicate_rows,
                status=batch.status,
            )
        if batch.status not in {"preview_ready", "validated"}:
            raise AppError(
                status_code=422,
                code="BATCH_NOT_VALIDATED",
                message="Run validation before committing batch.",
            )

        mapping_cfg = batch.column_mapping_jsonb
        source_id = UUID(mapping_cfg["source_id"])
        license_id = UUID(mapping_cfg["license_id"])
        await assert_license_usable(
            self.db, source_id=source_id, license_id=license_id, require_approved=False
        )

        allowed_statuses = {"valid", "warning"} if payload.include_warnings else {"valid"}
        rows = list(
            (
                await self.db.scalars(
                    select(ImportStagingRow)
                    .where(ImportStagingRow.import_batch_id == batch.id)
                    .order_by(ImportStagingRow.row_number)
                )
            ).all()
        )

        committed = 0
        skipped = 0
        for row in rows:
            if (
                row.validation_status not in allowed_statuses
                or row.normalized_payload_jsonb is None
            ):
                skipped += 1
                continue
            if row.created_question_id is not None:
                skipped += 1
                continue

            norm = row.normalized_payload_jsonb
            q = Question(
                canonical_hash=norm["canonical_hash"],
                question_type=norm["question_type"],
                status=payload.target_status,
                import_batch_id=batch.id,
                created_by=caller.id,
            )
            self.db.add(q)
            await self.db.flush()

            qv = QuestionVersion(
                question_id=q.id,
                version_no=1,
                language_code=norm["language_code"],
                curriculum_version_id=UUID(norm["resolved_curriculum_version_id"]),
                grade_id=UUID(norm["resolved_grade_id"]),
                subject_id=UUID(norm["resolved_subject_id"]),
                chapter_id=UUID(norm["resolved_chapter_id"]),
                topic_id=UUID(norm["resolved_topic_id"]) if norm.get("resolved_topic_id") else None,
                concept_id=(
                    UUID(norm["resolved_concept_id"]) if norm.get("resolved_concept_id") else None
                ),
                stem_markdown=norm["stem_markdown"],
                correct_answer_jsonb=norm["correct_answer_jsonb"],
                difficulty=norm["difficulty"],
                default_marks=Decimal(str(norm["default_marks"])),
                default_negative_marks=Decimal(str(norm["default_negative_marks"])),
                estimated_seconds=int(norm["estimated_seconds"]),
                ai_generated=False,
            )
            self.db.add(qv)
            await self.db.flush()
            q.current_version_id = qv.id

            for opt in norm.get("options", []):
                self.db.add(
                    QuestionOption(
                        question_version_id=qv.id,
                        option_key=opt["option_key"],
                        content_markdown=opt["content_markdown"],
                        is_correct=bool(opt["is_correct"]),
                    )
                )
            if norm.get("explanation"):
                self.db.add(
                    QuestionSolution(
                        question_version_id=qv.id,
                        language_code=norm["language_code"],
                        solution_type="primary",
                        explanation_markdown=norm["explanation"],
                        steps_jsonb=[],
                        common_mistakes_markdown=norm.get("common_mistakes"),
                    )
                )
            for h in norm.get("hints", []):
                self.db.add(
                    QuestionHint(
                        question_version_id=qv.id,
                        hint_level=h["hint_level"],
                        hint_markdown=h["hint_markdown"],
                    )
                )
            self.db.add(
                QuestionProvenance(
                    question_id=q.id,
                    source_id=source_id,
                    license_id=license_id,
                    source_type="licensed",
                    is_pyq=False,  # Reviewer must verify PYQ provenance separately.
                    exam_name=norm.get("exam_name"),
                    exam_year=norm.get("exam_year"),
                    source_url=norm.get("source_url"),
                    verification_status="unverified",
                )
            )
            row.created_question_id = q.id
            row.validation_status = "imported"
            committed += 1

        batch.status = "committed"
        batch.completed_at = datetime.now(UTC)
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="import.committed",
            resource_type="import_batch",
            resource_id=str(batch.id),
            metadata={"committed_count": committed, "skipped_count": skipped},
        )
        await self.db.commit()
        return ImportCommitResponse(
            batch_id=batch.id,
            committed_count=committed,
            skipped_count=skipped,
            status=batch.status,
        )

    async def rollback_batch(
        self, batch_id: UUID, caller: AuthenticatedUser
    ) -> ImportRollbackResponse:
        batch = await self.db.get(ImportBatch, batch_id)
        if batch is None:
            raise AppError(status_code=404, code="BATCH_NOT_FOUND", message="Import batch missing.")

        batch_questions = list(
            (
                await self.db.scalars(select(Question).where(Question.import_batch_id == batch.id))
            ).all()
        )
        published = [q for q in batch_questions if q.status == "PUBLISHED"]
        if published:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="ROLLBACK_BLOCKED_PUBLISHED",
                message=(
                    "Cannot rollback a batch containing PUBLISHED questions; archive them instead."
                ),
            )

        count = len(batch_questions)
        if batch_questions:
            await self.db.execute(delete(Question).where(Question.import_batch_id == batch.id))

        rows = list(
            (
                await self.db.scalars(
                    select(ImportStagingRow).where(ImportStagingRow.import_batch_id == batch.id)
                )
            ).all()
        )
        for row in rows:
            row.created_question_id = None
            row.validation_status = "rolled_back"

        batch.status = "rolled_back"
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="import.rolled_back",
            resource_type="import_batch",
            resource_id=str(batch.id),
            metadata={"rolled_back_questions": count},
        )
        await self.db.commit()
        return ImportRollbackResponse(
            batch_id=batch.id,
            rolled_back_questions=count,
            status=batch.status,
        )
