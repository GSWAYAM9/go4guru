"""Service layer for Phase 9: Examination Preparation Ecosystem.

Coordinates versioned exam configurations (CBSE Board, JEE Main, JEE Advanced, NEET),
syllabus & chapter mappings with honest coverage audits, strict verified-PYQ filtering,
chapter/topic practice and timed mock generation, exam analytics, formula sheets,
revision plans, and post-attempt detailed solutions.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.errors import AppError
from src.modules.assessment.exam_prep_logic import (
    EXAM_TARGET_SECONDS_PER_QUESTION,
    ChapterCoverageInput,
    ExamAnswerObservation,
    ExamAttemptHistoryInput,
    RevisionChapterCandidate,
    compute_exam_analytics,
    compute_exam_coverage_audit,
    generate_exam_revision_schedule,
)
from src.modules.assessment.exam_prep_models import (
    ExamFormulaSheet,
    ExamRevisionPlan,
    ExamSyllabusChapter,
)
from src.modules.assessment.exam_prep_schemas import (
    AttemptDetailedSolutionsResponse,
    DetailedSolutionItemOut,
    ExamAnalyticsResponse,
    ExamCoverageAuditOut,
    ExamFormulaCreate,
    ExamFormulaOut,
    ExamMockGenerateRequest,
    ExamPerformanceHistoryItemOut,
    ExamPracticeLaunchRequest,
    ExamQuestionFacetsOut,
    ExamQuestionItemOut,
    ExamQuestionOptionRedactedOut,
    ExamQuestionsExplorerResponse,
    ExamRevisionPlanCreate,
    ExamRevisionPlanOut,
    ExamSyllabusChapterOut,
    ExamSyllabusChapterUpsert,
    ExamSyllabusResponse,
    ExamTrackOverviewOut,
    FormulaVariableItem,
    LaunchedExamAttemptOut,
    SyllabusTopicItemOut,
    VerifiedPyqBadgeOut,
    WeaknessBucketOut,
)
from src.modules.assessment.exam_schemas import ExamPatternOut
from src.modules.assessment.exam_service import ExamAssessmentService
from src.modules.assessment.models import (
    AssessmentAttempt,
    AssessmentTemplate,
    AttemptAnswer,
    ExamPattern,
    Quiz,
    QuizQuestion,
    TestQuestion,
    TestSection,
)
from src.modules.assessment.rule_engine import ExamPatternRules, ScoringRule
from src.modules.curriculum.public import (
    ExamTrackContract,
    get_curriculum_catalog_maps,
    get_exam_track_by_code,
    list_exam_tracks_contracts,
)
from src.modules.question_bank.public import (
    get_exam_question_audit_stats,
    get_pinned_versions_map,
    list_questions_for_exam_prep,
)

EXAM_CODE_TO_TEST_CATEGORY: dict[str, str] = {
    "CBSE_BOARD": "cbse_mock",
    "JEE_MAIN": "jee_main",
    "JEE_ADVANCED": "jee_adv",
    "NEET": "neet",
}

MANAGER_ROLES = {"platform_admin", "school_admin", "content_admin", "academic_reviewer"}
EDUCATOR_ROLES = {"teacher", "mentor", "school_admin", "content_admin", "academic_reviewer", "platform_admin"}


def _require_exam_manager(caller: AuthenticatedUser) -> None:
    if not (
        caller.has_permission("exam_prep:manage")
        or caller.has_permission("exam_pattern:manage")
        or any(caller.has_role(r) for r in MANAGER_ROLES)
    ):
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Managing exam syllabus, rules, or formula sheets requires content/academic reviewer or admin privileges.",
        )


def _to_pattern_out(track: ExamTrackContract, row: ExamPattern) -> ExamPatternOut:
    return ExamPatternOut(
        id=row.id,
        exam_track_id=row.exam_track_id,
        exam_track_code=track.code,
        exam_track_name=track.name,
        version_label=row.version_label,
        effective_year=row.effective_year,
        is_active=row.is_active,
        rules=ExamPatternRules.model_validate(row.rules_jsonb),
    )


class ExamPrepService:
    """Orchestrates Phase 9 Exam Preparation Ecosystem workflows."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.assessment_svc = ExamAssessmentService(db)

    async def _resolve_track(self, exam_code: str) -> ExamTrackContract:
        track = await get_exam_track_by_code(self.db, exam_code)
        if track is None:
            raise AppError(
                status_code=404,
                code="EXAM_TRACK_NOT_FOUND",
                message=f"Examination track '{exam_code}' not found.",
            )
        return track

    async def _get_track_patterns(self, track_id: UUID) -> list[ExamPattern]:
        return list(
            (
                await self.db.scalars(
                    select(ExamPattern)
                    .where(ExamPattern.exam_track_id == track_id)
                    .order_by(ExamPattern.is_active.desc(), ExamPattern.effective_year.desc(), ExamPattern.created_at.desc())
                )
            ).all()
        )

    async def _compute_track_audit(
        self,
        *,
        track: ExamTrackContract,
        syllabus_rows: list[ExamSyllabusChapter],
    ) -> tuple[ExamCoverageAuditOut, Any]:
        scope_ids = {r.chapter_id for r in syllabus_rows} if syllabus_rows else None
        q_stats = await get_exam_question_audit_stats(
            self.db,
            exam_code=track.code,
            chapter_ids_scope=scope_ids,
        )
        chapter_inputs = [
            ChapterCoverageInput(
                chapter_id=str(r.chapter_id),
                audit_verified=bool(r.audit_verified),
                syllabus_status=r.syllabus_status,
                published_question_count=q_stats.chapter_published_counts.get(r.chapter_id, 0),
                verified_pyq_count=q_stats.chapter_verified_pyq_counts.get(r.chapter_id, 0),
            )
            for r in syllabus_rows
        ]
        audit = compute_exam_coverage_audit(
            exam_code=track.code,
            chapters=chapter_inputs,
            total_published_questions=q_stats.total_published_questions,
            total_verified_pyqs=q_stats.total_verified_pyqs,
            unverified_pyq_excluded_count=q_stats.unverified_pyq_excluded_count,
        )
        return (
            ExamCoverageAuditOut(
                exam_code=audit.exam_code,
                mapped_chapters_count=audit.mapped_chapters_count,
                included_chapters_count=audit.included_chapters_count,
                audited_chapters_count=audit.audited_chapters_count,
                chapters_with_questions_count=audit.chapters_with_questions_count,
                published_question_count=audit.published_question_count,
                verified_pyq_count=audit.verified_pyq_count,
                unverified_pyq_excluded_count=audit.unverified_pyq_excluded_count,
                audited_coverage_pct=audit.audited_coverage_pct,
                question_coverage_pct=audit.question_coverage_pct,
                coverage_status=audit.coverage_status,  # type: ignore[arg-type]
                coverage_disclaimer=audit.coverage_disclaimer,
            ),
            q_stats,
        )

    # ------------------------------------------------------------------
    # 1. Exam Tracks & Versioned Configurations
    # ------------------------------------------------------------------

    async def list_exam_tracks_overview(self) -> list[ExamTrackOverviewOut]:
        tracks = await list_exam_tracks_contracts(self.db)
        out: list[ExamTrackOverviewOut] = []
        for track in tracks:
            patterns = await self._get_track_patterns(track.id)
            pattern_outs = [_to_pattern_out(track, p) for p in patterns]
            active_pat = next((p for p in pattern_outs if p.is_active), pattern_outs[0] if pattern_outs else None)

            syl_stmt = select(ExamSyllabusChapter).where(ExamSyllabusChapter.exam_track_id == track.id)
            if active_pat is not None:
                syl_stmt = syl_stmt.where(
                    ExamSyllabusChapter.pattern_version_label == active_pat.version_label
                )
            syl_rows = list((await self.db.scalars(syl_stmt)).all())
            if not syl_rows:
                syl_rows = list(
                    (
                        await self.db.scalars(
                            select(ExamSyllabusChapter).where(
                                ExamSyllabusChapter.exam_track_id == track.id
                            )
                        )
                    ).all()
                )
            audit_out, _ = await self._compute_track_audit(track=track, syllabus_rows=syl_rows)
            out.append(
                ExamTrackOverviewOut(
                    id=track.id,
                    code=track.code,
                    name=track.name,
                    target_seconds_per_question=EXAM_TARGET_SECONDS_PER_QUESTION.get(track.code, 120),
                    active_pattern=active_pat,
                    patterns=pattern_outs,
                    coverage_audit=audit_out,
                )
            )
        return out

    # ------------------------------------------------------------------
    # 2. Syllabus & Chapter Mappings
    # ------------------------------------------------------------------

    async def get_exam_syllabus(
        self,
        *,
        exam_code: str,
        pattern_version_label: str | None = None,
    ) -> ExamSyllabusResponse:
        track = await self._resolve_track(exam_code)
        patterns = await self._get_track_patterns(track.id)
        resolved_ver = pattern_version_label
        if not resolved_ver:
            active = next((p for p in patterns if p.is_active), patterns[0] if patterns else None)
            resolved_ver = active.version_label if active else "default-v1"

        rows = list(
            (
                await self.db.scalars(
                    select(ExamSyllabusChapter)
                    .where(
                        ExamSyllabusChapter.exam_track_id == track.id,
                        ExamSyllabusChapter.pattern_version_label == resolved_ver,
                    )
                    .order_by(ExamSyllabusChapter.weightage_pct.desc())
                )
            ).all()
        )
        if not rows and pattern_version_label is None:
            # Fallback to any mapped version for this exam track if default version has none yet
            rows = list(
                (
                    await self.db.scalars(
                        select(ExamSyllabusChapter)
                        .where(ExamSyllabusChapter.exam_track_id == track.id)
                        .order_by(ExamSyllabusChapter.weightage_pct.desc())
                    )
                ).all()
            )
            if rows:
                resolved_ver = rows[0].pattern_version_label

        audit_out, q_stats = await self._compute_track_audit(track=track, syllabus_rows=rows)
        catalog = await get_curriculum_catalog_maps(self.db)

        chapters_out = [
            ExamSyllabusChapterOut(
                id=r.id,
                exam_track_id=r.exam_track_id,
                pattern_version_label=r.pattern_version_label,
                subject_id=r.subject_id,
                subject_name=catalog.subjects.get(r.subject_id, "Subject"),
                chapter_id=r.chapter_id,
                chapter_title=catalog.chapters.get(r.chapter_id, "Chapter"),
                weightage_pct=float(r.weightage_pct),
                expected_questions=r.expected_questions,
                priority_tier=r.priority_tier,  # type: ignore[arg-type]
                syllabus_status=r.syllabus_status,  # type: ignore[arg-type]
                notes=r.notes,
                audit_verified=bool(r.audit_verified),
                audited_at=r.audited_at,
                published_question_count=q_stats.chapter_published_counts.get(r.chapter_id, 0),
                verified_pyq_count=q_stats.chapter_verified_pyq_counts.get(r.chapter_id, 0),
                topics=[
                    SyllabusTopicItemOut(id=tid, title=ttitle)
                    for tid, ttitle in catalog.chapter_topics.get(r.chapter_id, ())
                ],
            )
            for r in rows
        ]

        return ExamSyllabusResponse(
            exam_code=track.code,
            exam_name=track.name,
            pattern_version_label=resolved_ver,
            coverage_audit=audit_out,
            chapters=chapters_out,
        )

    async def upsert_syllabus_chapter(
        self,
        *,
        exam_code: str,
        payload: ExamSyllabusChapterUpsert,
        caller: AuthenticatedUser,
    ) -> ExamSyllabusChapterOut:
        _require_exam_manager(caller)
        track = await self._resolve_track(exam_code)

        existing = await self.db.scalar(
            select(ExamSyllabusChapter).where(
                ExamSyllabusChapter.exam_track_id == track.id,
                ExamSyllabusChapter.pattern_version_label == payload.pattern_version_label.strip(),
                ExamSyllabusChapter.chapter_id == payload.chapter_id,
            )
        )
        now = datetime.now(UTC)
        if existing is None:
            row = ExamSyllabusChapter(
                exam_track_id=track.id,
                pattern_version_label=payload.pattern_version_label.strip(),
                subject_id=payload.subject_id,
                chapter_id=payload.chapter_id,
                weightage_pct=Decimal(str(payload.weightage_pct)),
                expected_questions=payload.expected_questions,
                priority_tier=payload.priority_tier,
                syllabus_status=payload.syllabus_status,
                notes=payload.notes,
                audit_verified=payload.audit_verified,
                audited_by=caller.id if payload.audit_verified else None,
                audited_at=now if payload.audit_verified else None,
            )
            self.db.add(row)
        else:
            existing.subject_id = payload.subject_id
            existing.weightage_pct = Decimal(str(payload.weightage_pct))
            existing.expected_questions = payload.expected_questions
            existing.priority_tier = payload.priority_tier
            existing.syllabus_status = payload.syllabus_status
            existing.notes = payload.notes
            existing.audit_verified = payload.audit_verified
            if payload.audit_verified:
                existing.audited_by = caller.id
                existing.audited_at = now
            else:
                existing.audited_by = None
                existing.audited_at = None
            row = existing

        await self.db.flush()
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="exam_prep.syllabus_chapter_upserted",
            resource_type="exam_syllabus_chapter",
            resource_id=str(row.id),
            metadata={
                "exam_code": track.code,
                "chapter_id": str(row.chapter_id),
                "audit_verified": row.audit_verified,
            },
        )
        await self.db.commit()
        await self.db.refresh(row)

        catalog = await get_curriculum_catalog_maps(self.db)
        q_stats = await get_exam_question_audit_stats(
            self.db, exam_code=track.code, chapter_ids_scope={row.chapter_id}
        )
        return ExamSyllabusChapterOut(
            id=row.id,
            exam_track_id=row.exam_track_id,
            pattern_version_label=row.pattern_version_label,
            subject_id=row.subject_id,
            subject_name=catalog.subjects.get(row.subject_id, "Subject"),
            chapter_id=row.chapter_id,
            chapter_title=catalog.chapters.get(row.chapter_id, "Chapter"),
            weightage_pct=float(row.weightage_pct),
            expected_questions=row.expected_questions,
            priority_tier=row.priority_tier,  # type: ignore[arg-type]
            syllabus_status=row.syllabus_status,  # type: ignore[arg-type]
            notes=row.notes,
            audit_verified=bool(row.audit_verified),
            audited_at=row.audited_at,
            published_question_count=q_stats.chapter_published_counts.get(row.chapter_id, 0),
            verified_pyq_count=q_stats.chapter_verified_pyq_counts.get(row.chapter_id, 0),
            topics=[
                SyllabusTopicItemOut(id=tid, title=ttitle)
                for tid, ttitle in catalog.chapter_topics.get(row.chapter_id, ())
            ],
        )

    # ------------------------------------------------------------------
    # 3. Verified PYQ & Filtered Question Explorer (Answers Redacted)
    # ------------------------------------------------------------------

    async def explore_exam_questions(
        self,
        *,
        exam_code: str,
        verified_pyq_only: bool = False,
        exam_year: int | None = None,
        exam_session: str | None = None,
        difficulty: str | None = None,
        question_type: str | None = None,
        subject_id: UUID | None = None,
        chapter_id: UUID | None = None,
        topic_id: UUID | None = None,
        concept_id: UUID | None = None,
        limit: int = 30,
    ) -> ExamQuestionsExplorerResponse:
        track = await self._resolve_track(exam_code)
        syl_rows = list(
            (
                await self.db.scalars(
                    select(ExamSyllabusChapter).where(
                        ExamSyllabusChapter.exam_track_id == track.id,
                        ExamSyllabusChapter.syllabus_status != "excluded",
                    )
                )
            ).all()
        )
        scope_ids = {r.chapter_id for r in syl_rows} if syl_rows and not verified_pyq_only else None

        q_stats = await get_exam_question_audit_stats(
            self.db,
            exam_code=track.code,
            chapter_ids_scope=scope_ids,
        )
        items = await list_questions_for_exam_prep(
            self.db,
            exam_code=track.code,
            verified_pyq_only=verified_pyq_only,
            exam_year=exam_year,
            exam_session=exam_session,
            difficulty=difficulty,
            question_type=question_type,
            subject_id=subject_id,
            chapter_id=chapter_id,
            topic_id=topic_id,
            concept_id=concept_id,
            chapter_ids_scope=scope_ids if not chapter_id else None,
            limit=limit,
        )
        catalog = await get_curriculum_catalog_maps(self.db)

        return ExamQuestionsExplorerResponse(
            exam_code=track.code,
            verified_pyq_only=verified_pyq_only,
            facets=ExamQuestionFacetsOut(
                available_years=list(q_stats.available_years),
                available_sessions=list(q_stats.available_sessions),
                available_difficulties=list(q_stats.available_difficulties),
                available_question_types=list(q_stats.available_question_types),
                total_published_questions=q_stats.total_published_questions,
                total_verified_pyqs=q_stats.total_verified_pyqs,
                unverified_pyq_excluded_count=q_stats.unverified_pyq_excluded_count,
            ),
            questions=[
                ExamQuestionItemOut(
                    question_id=q.question_id,
                    question_version_id=q.question_version_id,
                    question_type=q.question_type,
                    subject_id=q.subject_id,
                    subject_name=catalog.subjects.get(q.subject_id, "Subject"),
                    chapter_id=q.chapter_id,
                    chapter_title=catalog.chapters.get(q.chapter_id, "Chapter"),
                    topic_id=q.topic_id,
                    topic_title=catalog.topics.get(q.topic_id) if q.topic_id else None,
                    concept_id=q.concept_id,
                    concept_title=catalog.concepts.get(q.concept_id) if q.concept_id else None,
                    stem_markdown=q.stem_markdown,
                    difficulty=q.difficulty,
                    default_marks=q.default_marks,
                    default_negative_marks=q.default_negative_marks,
                    estimated_seconds=q.estimated_seconds,
                    options=[
                        ExamQuestionOptionRedactedOut(option_key=k, content_markdown=txt)
                        for k, txt in q.options
                    ],
                    pyq_provenance=(
                        VerifiedPyqBadgeOut(
                            is_verified_pyq=True,
                            badge_label=q.pyq_provenance.badge_label,
                            exam_name=q.pyq_provenance.exam_name,
                            exam_year=q.pyq_provenance.exam_year,
                            exam_session=q.pyq_provenance.exam_session,
                            exam_shift=q.pyq_provenance.exam_shift,
                            paper_code=q.pyq_provenance.paper_code,
                            question_number=q.pyq_provenance.question_number,
                            source_url=q.pyq_provenance.source_url,
                            verification_status="verified",
                        )
                        if q.pyq_provenance is not None
                        else None
                    ),
                )
                for q in items
            ],
        )

    # ------------------------------------------------------------------
    # 4. Launch Chapter/Topic/Verified-PYQ Practice & Full Timed Mocks
    # ------------------------------------------------------------------

    async def launch_exam_practice(
        self,
        *,
        exam_code: str,
        payload: ExamPracticeLaunchRequest,
        caller: AuthenticatedUser,
    ) -> LaunchedExamAttemptOut:
        track = await self._resolve_track(exam_code)
        patterns = await self._get_track_patterns(track.id)
        pattern: ExamPattern | None = None
        if payload.exam_pattern_id:
            pattern = await self.db.get(ExamPattern, payload.exam_pattern_id)
            if pattern is None or pattern.exam_track_id != track.id:
                raise AppError(
                    status_code=404,
                    code="PATTERN_NOT_FOUND",
                    message="Requested exam pattern does not belong to this exam track.",
                )
        elif patterns:
            pattern = next((p for p in patterns if p.is_active), patterns[0])

        scoring_rule = ScoringRule(mode="standard", correct_marks=4.0, wrong_marks=-1.0)
        if pattern is not None:
            parsed_rules = ExamPatternRules.model_validate(pattern.rules_jsonb)
            if parsed_rules.sections:
                scoring_rule = parsed_rules.sections[0].scoring

        selected = await list_questions_for_exam_prep(
            self.db,
            exam_code=track.code,
            verified_pyq_only=payload.verified_pyq_only or payload.mode == "verified_pyq_drill",
            exam_year=payload.exam_year,
            exam_session=payload.exam_session,
            difficulty=payload.difficulty,
            question_type=payload.question_type,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            limit=payload.question_count,
        )
        if not selected:
            raise AppError(
                status_code=422,
                code="NO_MATCHING_EXAM_QUESTIONS",
                message=(
                    "No verified PYQs matched these filters."
                    if (payload.verified_pyq_only or payload.mode == "verified_pyq_drill")
                    else "No PUBLISHED questions matched the requested exam practice filters."
                ),
            )

        target_sec = EXAM_TARGET_SECONDS_PER_QUESTION.get(track.code, 120)
        duration = payload.duration_seconds or max(300, len(selected) * target_sec)
        quiz_title = (
            payload.title.strip()
            if payload.title and payload.title.strip()
            else f"{track.name} · {payload.mode.replace('_', ' ').title()}"
        )

        quiz = Quiz(
            tenant_id=caller.tenant_id,
            quiz_type="exam_practice",
            title=quiz_title,
            created_by=caller.id,
            exam_pattern_id=pattern.id if pattern else None,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            config_jsonb={
                "exam_code": track.code,
                "practice_mode": payload.mode,
                "verified_pyq_only": payload.verified_pyq_only or payload.mode == "verified_pyq_drill",
                "duration_seconds": duration,
                "grace_seconds": 30,
                "shuffle_questions": False,
                "shuffle_options": False,
                "scoring_rule": scoring_rule.model_dump(),
                "seed": 42,
            },
            is_ai_generated=False,
            status="PUBLISHED",
        )
        self.db.add(quiz)
        await self.db.flush()

        for seq, q in enumerate(selected, start=1):
            self.db.add(
                QuizQuestion(
                    quiz_id=quiz.id,
                    sequence_no=seq,
                    question_id=q.question_id,
                    question_version_id=q.question_version_id,
                    marks_override=Decimal(str(scoring_rule.correct_marks)),
                    negative_marks_override=Decimal(str(abs(scoring_rule.wrong_marks))),
                )
            )
        await self.db.commit()

        attempt_state = await self.assessment_svc.start_quiz_attempt(quiz.id, caller)
        return LaunchedExamAttemptOut(
            attempt_id=attempt_state.attempt_id,
            exam_code=track.code,
            test_id=None,
            quiz_id=quiz.id,
            title=quiz.title,
            pattern_version_label=pattern.version_label if pattern else None,
            question_count=len(selected),
            duration_seconds=duration,
            started_at=attempt_state.started_at,
            expires_at=attempt_state.expires_at,
        )

    async def generate_and_start_mock_test(
        self,
        *,
        exam_code: str,
        payload: ExamMockGenerateRequest,
        caller: AuthenticatedUser,
    ) -> LaunchedExamAttemptOut:
        track = await self._resolve_track(exam_code)
        patterns = await self._get_track_patterns(track.id)
        pattern: ExamPattern | None = None
        if payload.exam_pattern_id:
            pattern = await self.db.get(ExamPattern, payload.exam_pattern_id)
            if pattern is None or pattern.exam_track_id != track.id:
                raise AppError(
                    status_code=404,
                    code="PATTERN_NOT_FOUND",
                    message="Requested exam pattern does not belong to this exam track.",
                )
        elif patterns:
            pattern = next((p for p in patterns if p.is_active), patterns[0])

        if pattern is None:
            raise AppError(
                status_code=422,
                code="NO_ACTIVE_EXAM_PATTERN",
                message=f"No configured versioned ExamPattern exists for {track.name}.",
            )

        rules = ExamPatternRules.model_validate(pattern.rules_jsonb)
        if not rules.sections:
            raise AppError(
                status_code=422,
                code="EMPTY_EXAM_PATTERN_SECTIONS",
                message="ExamPattern must define at least one section before generating a mock.",
            )

        test_category = EXAM_CODE_TO_TEST_CATEGORY.get(track.code, "cbse_mock")
        mock_title = (
            payload.title.strip()
            if payload.title and payload.title.strip()
            else f"{track.name} Timed Mock ({pattern.version_label})"
        )

        # Assemble sections strictly from PUBLISHED questions honoring section question types
        used_question_ids: set[UUID] = set()
        assembled_sections: list[tuple[Any, list[Any]]] = []
        total_marks = Decimal("0.00")
        total_questions = 0

        for sec_rule in rules.sections:
            sec_candidates = []
            allowed_types = sec_rule.allowed_question_types or None
            if allowed_types:
                for qtype in allowed_types:
                    found = await list_questions_for_exam_prep(
                        self.db,
                        exam_code=track.code,
                        verified_pyq_only=payload.verified_pyq_only,
                        question_type=qtype,
                        subject_id=payload.subject_id,
                        chapter_id=payload.chapter_id,
                        limit=sec_rule.question_count + len(used_question_ids),
                    )
                    for item in found:
                        if item.question_id not in used_question_ids:
                            sec_candidates.append(item)
                            used_question_ids.add(item.question_id)
                        if len(sec_candidates) >= sec_rule.question_count:
                            break
                    if len(sec_candidates) >= sec_rule.question_count:
                        break
            else:
                found = await list_questions_for_exam_prep(
                    self.db,
                    exam_code=track.code,
                    verified_pyq_only=payload.verified_pyq_only,
                    subject_id=payload.subject_id,
                    chapter_id=payload.chapter_id,
                    limit=sec_rule.question_count + len(used_question_ids),
                )
                for item in found:
                    if item.question_id not in used_question_ids:
                        sec_candidates.append(item)
                        used_question_ids.add(item.question_id)
                    if len(sec_candidates) >= sec_rule.question_count:
                        break

            if sec_candidates:
                assembled_sections.append((sec_rule, sec_candidates))
                countable = (
                    min(len(sec_candidates), sec_rule.attempt_limit)
                    if sec_rule.attempt_limit
                    else len(sec_candidates)
                )
                total_marks += Decimal(str(countable * sec_rule.scoring.correct_marks))
                total_questions += len(sec_candidates)

        if total_questions == 0:
            raise AppError(
                status_code=422,
                code="INSUFFICIENT_PUBLISHED_QUESTIONS",
                message=(
                    f"No PUBLISHED questions are available matching the {pattern.version_label} "
                    "section rules. Publish or verify questions before launching a timed mock."
                ),
            )

        test = AssessmentTemplate(
            tenant_id=caller.tenant_id,
            exam_pattern_id=pattern.id,
            title=mock_title,
            description=f"Auto-assembled from versioned blueprint {pattern.version_label} ({total_questions} questions).",
            test_category=test_category,
            duration_seconds=rules.duration_seconds,
            grace_seconds=rules.grace_seconds,
            total_marks=total_marks,
            retake_policy_jsonb=rules.retake_policy.model_dump(),
            shuffle_questions=rules.shuffle_questions,
            shuffle_options=rules.shuffle_options,
            created_by=caller.id,
            status="PUBLISHED",
            published_at=datetime.now(UTC),
        )
        self.db.add(test)
        await self.db.flush()

        for s_seq, (sec_rule, items) in enumerate(assembled_sections, start=1):
            t_sec = TestSection(
                test_id=test.id,
                sequence_no=s_seq,
                name=sec_rule.name,
                subject_id=payload.subject_id,
                marking_rule_jsonb=sec_rule.scoring.model_dump(),
                duration_seconds=None,
                attempt_limit=sec_rule.attempt_limit,
            )
            self.db.add(t_sec)
            await self.db.flush()

            for q_seq, q_item in enumerate(items, start=1):
                self.db.add(
                    TestQuestion(
                        test_id=test.id,
                        section_id=t_sec.id,
                        question_id=q_item.question_id,
                        question_version_id=q_item.question_version_id,
                        sequence_no=q_seq,
                        marks_override=Decimal(str(sec_rule.scoring.correct_marks)),
                        negative_marks_override=Decimal(str(abs(sec_rule.scoring.wrong_marks))),
                    )
                )

        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="exam_prep.timed_mock_generated",
            resource_type="test",
            resource_id=str(test.id),
            metadata={
                "exam_code": track.code,
                "pattern_version": pattern.version_label,
                "question_count": total_questions,
            },
        )
        await self.db.commit()

        attempt_state = await self.assessment_svc.start_test_attempt(test.id, caller)
        return LaunchedExamAttemptOut(
            attempt_id=attempt_state.attempt_id,
            exam_code=track.code,
            test_id=test.id,
            quiz_id=None,
            title=test.title,
            pattern_version_label=pattern.version_label,
            question_count=total_questions,
            duration_seconds=test.duration_seconds,
            started_at=attempt_state.started_at,
            expires_at=attempt_state.expires_at,
        )

    # ------------------------------------------------------------------
    # 5. Exam Analytics (Accuracy, Speed, Weak Areas, History, Advice)
    # ------------------------------------------------------------------

    async def get_student_exam_analytics(
        self,
        *,
        exam_code: str,
        student_id: UUID,
    ) -> ExamAnalyticsResponse:
        track = await self._resolve_track(exam_code)
        patterns = await self._get_track_patterns(track.id)
        pattern_ids = {p.id for p in patterns}
        target_cat = EXAM_CODE_TO_TEST_CATEGORY.get(track.code)

        # Gather all submitted/graded attempts belonging to this student & exam track
        attempts = list(
            (
                await self.db.scalars(
                    select(AssessmentAttempt)
                    .where(
                        AssessmentAttempt.student_id == student_id,
                        AssessmentAttempt.status.in_(["submitted", "auto_submitted", "graded"]),
                    )
                    .order_by(AssessmentAttempt.submitted_at.asc())
                )
            ).all()
        )

        test_ids = [a.test_id for a in attempts if a.test_id is not None]
        quiz_ids = [a.quiz_id for a in attempts if a.quiz_id is not None]
        tests_map = (
            {
                t.id: t
                for t in (
                    await self.db.scalars(
                        select(AssessmentTemplate).where(AssessmentTemplate.id.in_(test_ids))
                    )
                ).all()
            }
            if test_ids
            else {}
        )
        quizzes_map = (
            {
                q.id: q
                for q in (await self.db.scalars(select(Quiz).where(Quiz.id.in_(quiz_ids)))).all()
            }
            if quiz_ids
            else {}
        )

        matching_attempts: list[tuple[AssessmentAttempt, str, str]] = []
        for att in attempts:
            if att.test_id and att.test_id in tests_map:
                t = tests_map[att.test_id]
                if t.test_category == target_cat or (t.exam_pattern_id in pattern_ids):
                    matching_attempts.append((att, t.title, t.test_category))
            elif att.quiz_id and att.quiz_id in quizzes_map:
                q = quizzes_map[att.quiz_id]
                cfg_code = str((q.config_jsonb or {}).get("exam_code", "")).upper()
                if cfg_code == track.code or (q.exam_pattern_id in pattern_ids):
                    matching_attempts.append((att, q.title, q.quiz_type))

        att_ids = [a.id for a, _, _ in matching_attempts]
        answers = (
            list(
                (
                    await self.db.scalars(
                        select(AttemptAnswer).where(AttemptAnswer.attempt_id.in_(att_ids))
                    )
                ).all()
            )
            if att_ids
            else []
        )

        qv_ids = list({ans.question_version_id for ans in answers})
        pinned = await get_pinned_versions_map(self.db, qv_ids)
        catalog = await get_curriculum_catalog_maps(self.db)

        answers_by_attempt: dict[UUID, list[AttemptAnswer]] = {}
        for ans in answers:
            answers_by_attempt.setdefault(ans.attempt_id, []).append(ans)

        observations: list[ExamAnswerObservation] = []
        history_inputs: list[ExamAttemptHistoryInput] = []
        history_dt_map: dict[str, datetime] = {}

        for att, title, category in matching_attempts:
            att_ans = answers_by_attempt.get(att.id, [])
            timed_vals = [int(a.time_spent_seconds) for a in att_ans if int(a.time_spent_seconds) > 0]
            avg_s = round(sum(timed_vals) / len(timed_vals), 1) if timed_vals else 0.0
            sub_dt = att.submitted_at or att.updated_at
            sub_iso = sub_dt.isoformat()
            history_dt_map[str(att.id)] = sub_dt
            history_inputs.append(
                ExamAttemptHistoryInput(
                    attempt_id=str(att.id),
                    title=title,
                    category=category,
                    submitted_at_iso=sub_iso,
                    raw_score=float(att.raw_score or 0.0),
                    max_score=float(att.max_score or 0.0),
                    accuracy_pct=float(att.accuracy_pct or 0.0),
                    avg_seconds_per_question=avg_s,
                )
            )

            for ans in att_ans:
                pq = pinned.get(ans.question_version_id)
                if pq is None:
                    continue
                attempted_flag = bool(ans.response_jsonb)
                observations.append(
                    ExamAnswerObservation(
                        attempt_id=str(att.id),
                        subject_id=str(pq.subject_id),
                        subject_name=catalog.subjects.get(pq.subject_id, "Subject"),
                        chapter_id=str(pq.chapter_id),
                        chapter_title=catalog.chapters.get(pq.chapter_id, "Chapter"),
                        concept_id=str(pq.concept_id) if pq.concept_id else None,
                        concept_title=catalog.concepts.get(pq.concept_id) if pq.concept_id else None,
                        is_correct=bool(ans.is_correct),
                        attempted=attempted_flag,
                        marks_awarded=float(ans.marks_awarded or 0.0),
                        max_marks=pq.default_marks,
                        time_spent_seconds=int(ans.time_spent_seconds or 0),
                    )
                )

        summary = compute_exam_analytics(
            exam_code=track.code,
            observations=observations,
            history=history_inputs,
        )

        return ExamAnalyticsResponse(
            exam_code=track.code,
            exam_name=track.name,
            total_attempts=summary.total_attempts,
            total_questions_answered=summary.total_questions_answered,
            overall_accuracy_pct=summary.overall_accuracy_pct,
            average_seconds_per_question=summary.average_seconds_per_question,
            target_seconds_per_question=summary.target_seconds_per_question,
            pacing_status=summary.pacing_status,
            weak_subjects=[
                WeaknessBucketOut(
                    entity_id=w.entity_id,
                    name=w.name,
                    attempts=w.attempts,
                    correct=w.correct,
                    accuracy_pct=w.accuracy_pct,
                    avg_seconds=w.avg_seconds,
                    severity=w.severity,  # type: ignore[arg-type]
                )
                for w in summary.weak_subjects
            ],
            weak_chapters=[
                WeaknessBucketOut(
                    entity_id=w.entity_id,
                    name=w.name,
                    attempts=w.attempts,
                    correct=w.correct,
                    accuracy_pct=w.accuracy_pct,
                    avg_seconds=w.avg_seconds,
                    severity=w.severity,  # type: ignore[arg-type]
                )
                for w in summary.weak_chapters
            ],
            weak_concepts=[
                WeaknessBucketOut(
                    entity_id=w.entity_id,
                    name=w.name,
                    attempts=w.attempts,
                    correct=w.correct,
                    accuracy_pct=w.accuracy_pct,
                    avg_seconds=w.avg_seconds,
                    severity=w.severity,  # type: ignore[arg-type]
                )
                for w in summary.weak_concepts
            ],
            performance_history=[
                ExamPerformanceHistoryItemOut(
                    attempt_id=UUID(h.attempt_id),
                    title=h.title,
                    category=h.category,
                    submitted_at=history_dt_map[h.attempt_id],
                    raw_score=h.raw_score,
                    max_score=h.max_score,
                    accuracy_pct=h.accuracy_pct,
                    avg_seconds_per_question=h.avg_seconds_per_question,
                )
                for h in summary.performance_history
            ],
            improvement_recommendations=list(summary.improvement_recommendations),
        )

    # ------------------------------------------------------------------
    # 6. Formula Revision Sheets
    # ------------------------------------------------------------------

    async def list_formula_sheets(
        self,
        *,
        exam_code: str,
        subject_id: UUID | None = None,
        chapter_id: UUID | None = None,
        high_yield_only: bool = False,
    ) -> list[ExamFormulaOut]:
        track = await self._resolve_track(exam_code)
        stmt = select(ExamFormulaSheet).where(
            ExamFormulaSheet.exam_track_id == track.id,
            ExamFormulaSheet.status == "PUBLISHED",
        )
        if subject_id:
            stmt = stmt.where(ExamFormulaSheet.subject_id == subject_id)
        if chapter_id:
            stmt = stmt.where(ExamFormulaSheet.chapter_id == chapter_id)
        if high_yield_only:
            stmt = stmt.where(ExamFormulaSheet.is_high_yield.is_(True))

        rows = list(
            (
                await self.db.scalars(
                    stmt.order_by(ExamFormulaSheet.is_high_yield.desc(), ExamFormulaSheet.title.asc())
                )
            ).all()
        )
        catalog = await get_curriculum_catalog_maps(self.db)
        return [
            ExamFormulaOut(
                id=r.id,
                exam_track_id=r.exam_track_id,
                subject_id=r.subject_id,
                subject_name=catalog.subjects.get(r.subject_id, "Subject"),
                chapter_id=r.chapter_id,
                chapter_title=catalog.chapters.get(r.chapter_id, "Chapter"),
                topic_id=r.topic_id,
                topic_title=catalog.topics.get(r.topic_id) if r.topic_id else None,
                title=r.title,
                formula_latex=r.formula_latex,
                variables=[FormulaVariableItem.model_validate(v) for v in (r.variables_jsonb or [])],
                when_to_use=r.when_to_use,
                common_pitfall=r.common_pitfall,
                difficulty=r.difficulty,
                is_high_yield=bool(r.is_high_yield),
                status=r.status,
            )
            for r in rows
        ]

    async def create_formula_sheet(
        self,
        *,
        exam_code: str,
        payload: ExamFormulaCreate,
        caller: AuthenticatedUser,
    ) -> ExamFormulaOut:
        _require_exam_manager(caller)
        track = await self._resolve_track(exam_code)
        row = ExamFormulaSheet(
            exam_track_id=track.id,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
            title=payload.title.strip(),
            formula_latex=payload.formula_latex.strip(),
            variables_jsonb=[v.model_dump() for v in payload.variables],
            when_to_use=payload.when_to_use.strip(),
            common_pitfall=payload.common_pitfall.strip() if payload.common_pitfall else None,
            difficulty=payload.difficulty,
            is_high_yield=payload.is_high_yield,
            status=payload.status,
            created_by=caller.id,
        )
        self.db.add(row)
        await self.db.flush()
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="exam_prep.formula_created",
            resource_type="exam_formula_sheet",
            resource_id=str(row.id),
            metadata={"exam_code": track.code, "title": row.title},
        )
        await self.db.commit()
        await self.db.refresh(row)

        catalog = await get_curriculum_catalog_maps(self.db)
        return ExamFormulaOut(
            id=row.id,
            exam_track_id=row.exam_track_id,
            subject_id=row.subject_id,
            subject_name=catalog.subjects.get(row.subject_id, "Subject"),
            chapter_id=row.chapter_id,
            chapter_title=catalog.chapters.get(row.chapter_id, "Chapter"),
            topic_id=row.topic_id,
            topic_title=catalog.topics.get(row.topic_id) if row.topic_id else None,
            title=row.title,
            formula_latex=row.formula_latex,
            variables=payload.variables,
            when_to_use=row.when_to_use,
            common_pitfall=row.common_pitfall,
            difficulty=row.difficulty,
            is_high_yield=bool(row.is_high_yield),
            status=row.status,
        )

    # ------------------------------------------------------------------
    # 7. Exam Revision Plans
    # ------------------------------------------------------------------

    async def list_revision_plans(
        self,
        *,
        exam_code: str,
        student_id: UUID,
    ) -> list[ExamRevisionPlanOut]:
        track = await self._resolve_track(exam_code)
        rows = list(
            (
                await self.db.scalars(
                    select(ExamRevisionPlan)
                    .where(
                        ExamRevisionPlan.student_id == student_id,
                        ExamRevisionPlan.exam_track_id == track.id,
                    )
                    .order_by(ExamRevisionPlan.created_at.desc())
                )
            ).all()
        )
        return [
            ExamRevisionPlanOut(
                id=r.id,
                exam_track_id=r.exam_track_id,
                exam_code=track.code,
                exam_pattern_id=r.exam_pattern_id,
                title=r.title,
                target_exam_date=r.target_exam_date,
                daily_minutes=r.daily_minutes,
                focus_chapters=list(r.focus_chapters_jsonb or []),
                schedule=list(r.schedule_jsonb or []),
                status=r.status,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def create_revision_plan(
        self,
        *,
        exam_code: str,
        payload: ExamRevisionPlanCreate,
        caller: AuthenticatedUser,
    ) -> ExamRevisionPlanOut:
        track = await self._resolve_track(exam_code)
        today = date.today()
        if payload.target_exam_date < today:
            raise AppError(
                status_code=422,
                code="INVALID_TARGET_DATE",
                message="Target exam date must be today or in the future.",
            )

        syllabus = await self.get_exam_syllabus(exam_code=track.code)
        analytics = await self.get_student_exam_analytics(exam_code=track.code, student_id=caller.id)
        weak_acc_by_chap = {
            w.entity_id: w.accuracy_pct for w in analytics.weak_chapters if w.entity_id
        }

        focus_set = {str(cid) for cid in payload.focus_chapter_ids}
        candidates: list[RevisionChapterCandidate] = []
        for ch in syllabus.chapters:
            if ch.syllabus_status == "excluded":
                continue
            if focus_set and str(ch.chapter_id) not in focus_set:
                continue
            candidates.append(
                RevisionChapterCandidate(
                    chapter_id=str(ch.chapter_id),
                    chapter_title=ch.chapter_title,
                    subject_name=ch.subject_name,
                    weightage_pct=ch.weightage_pct,
                    priority_tier=ch.priority_tier,
                    student_accuracy_pct=weak_acc_by_chap.get(str(ch.chapter_id)),
                    verified_pyq_count=ch.verified_pyq_count,
                )
            )

        schedule = generate_exam_revision_schedule(
            exam_code=track.code,
            start_date=today,
            target_exam_date=payload.target_exam_date,
            daily_minutes=payload.daily_minutes,
            chapters=candidates,
        )
        focus_summary = [
            {
                "chapter_id": c.chapter_id,
                "chapter_title": c.chapter_title,
                "subject_name": c.subject_name,
                "weightage_pct": c.weightage_pct,
                "priority_tier": c.priority_tier,
                "student_accuracy_pct": c.student_accuracy_pct,
            }
            for c in candidates[:8]
        ]

        plan_title = (
            payload.title.strip()
            if payload.title and payload.title.strip()
            else f"{track.name} Revision Sprint ({payload.target_exam_date.isoformat()})"
        )
        plan = ExamRevisionPlan(
            student_id=caller.id,
            exam_track_id=track.id,
            exam_pattern_id=payload.exam_pattern_id,
            title=plan_title,
            target_exam_date=payload.target_exam_date,
            daily_minutes=payload.daily_minutes,
            focus_chapters_jsonb=focus_summary,
            schedule_jsonb=schedule,
            status="active",
        )
        self.db.add(plan)
        await self.db.flush()
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="exam_prep.revision_plan_created",
            resource_type="exam_revision_plan",
            resource_id=str(plan.id),
            metadata={"exam_code": track.code, "days_planned": len(schedule)},
        )
        await self.db.commit()
        await self.db.refresh(plan)
        return ExamRevisionPlanOut(
            id=plan.id,
            exam_track_id=plan.exam_track_id,
            exam_code=track.code,
            exam_pattern_id=plan.exam_pattern_id,
            title=plan.title,
            target_exam_date=plan.target_exam_date,
            daily_minutes=plan.daily_minutes,
            focus_chapters=list(plan.focus_chapters_jsonb or []),
            schedule=list(plan.schedule_jsonb or []),
            status=plan.status,
            created_at=plan.created_at,
        )

    # ------------------------------------------------------------------
    # 8. Detailed Post-Attempt Solutions (Strictly Locked Until Submitted)
    # ------------------------------------------------------------------

    async def get_attempt_detailed_solutions(
        self,
        *,
        attempt_id: UUID,
        caller: AuthenticatedUser,
    ) -> AttemptDetailedSolutionsResponse:
        attempt = await self.db.get(AssessmentAttempt, attempt_id)
        if attempt is None:
            raise AppError(
                status_code=404,
                code="ATTEMPT_NOT_FOUND",
                message="Assessment attempt not found.",
            )

        is_owner = attempt.student_id == caller.id
        is_educator = any(caller.has_role(r) for r in EDUCATOR_ROLES)
        if not (is_owner or is_educator):
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="You are not authorized to view solutions for this attempt.",
            )

        if attempt.status not in {"submitted", "auto_submitted", "graded"}:
            raise AppError(
                status_code=403,
                code="SOLUTIONS_LOCKED_DURING_ATTEMPT",
                message="Detailed answers and solutions remain locked until the attempt is submitted.",
            )

        title = "Assessment Attempt"
        if attempt.test_id:
            t = await self.db.get(AssessmentTemplate, attempt.test_id)
            if t:
                title = t.title
        elif attempt.quiz_id:
            q = await self.db.get(Quiz, attempt.quiz_id)
            if q:
                title = q.title

        ans_rows = list(
            (
                await self.db.scalars(
                    select(AttemptAnswer)
                    .where(AttemptAnswer.attempt_id == attempt.id)
                    .order_by(AttemptAnswer.sequence_no.asc())
                )
            ).all()
        )
        qv_ids = [a.question_version_id for a in ans_rows]
        pinned = await get_pinned_versions_map(self.db, qv_ids)
        catalog = await get_curriculum_catalog_maps(self.db)

        items: list[DetailedSolutionItemOut] = []
        for ans in ans_rows:
            pq = pinned.get(ans.question_version_id)
            if pq is None:
                continue
            items.append(
                DetailedSolutionItemOut(
                    sequence_no=ans.sequence_no,
                    question_id=pq.question_id,
                    question_version_id=pq.question_version_id,
                    question_type=pq.question_type,
                    subject_name=catalog.subjects.get(pq.subject_id, "Subject"),
                    chapter_title=catalog.chapters.get(pq.chapter_id, "Chapter"),
                    stem_markdown=pq.stem_markdown,
                    options=[
                        ExamQuestionOptionRedactedOut(option_key=k, content_markdown=txt)
                        for k, txt, _ in pq.options
                    ],
                    student_response_jsonb=dict(ans.response_jsonb or {}),
                    correct_answer_jsonb=dict(pq.correct_answer_jsonb or {}),
                    is_correct=ans.is_correct,
                    marks_awarded=float(ans.marks_awarded or 0.0),
                    time_spent_seconds=int(ans.time_spent_seconds or 0),
                    explanation_markdown=pq.explanation_markdown,
                    steps=list(pq.steps),
                    common_mistakes_markdown=pq.common_mistakes_markdown,
                )
            )

        return AttemptDetailedSolutionsResponse(
            attempt_id=attempt.id,
            title=title,
            status=attempt.status,
            raw_score=float(attempt.raw_score or 0.0),
            max_score=float(attempt.max_score or 0.0),
            accuracy_pct=float(attempt.accuracy_pct or 0.0),
            submitted_at=attempt.submitted_at,
            items=items,
        )
