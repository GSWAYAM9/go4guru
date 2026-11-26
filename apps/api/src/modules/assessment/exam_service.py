"""Server-authoritative Quiz & Assessment lifecycle engine with concurrency & idempotency."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.errors import AppError
from src.core.outbox import OutboxEvent
from src.modules.assessment.exam_schemas import (
    AttemptHistoryItem,
    AttemptQuestionOptionView,
    AttemptQuestionStateItem,
    AttemptResultQuestionItem,
    AttemptResultResponse,
    AttemptStateResponse,
    AutosaveAnswersRequest,
    AutosaveResponse,
    ExamPatternCreate,
    ExamPatternOut,
    QuizGenerateRequest,
    QuizOut,
    SectionScoreSummary,
    SubmitAttemptRequest,
    TestCreateRequest,
    TestOut,
    TestSectionOut,
)
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
from src.modules.assessment.rule_engine import (
    ExamPatternRules,
    ScoringRule,
    evaluate_question_with_rule,
    is_response_empty,
)
from src.modules.curriculum.public import get_exam_tracks_map
from src.modules.question_bank.public import (
    PinnedQuestionContract,
    get_pinned_versions_map,
    select_questions_for_assessment,
)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class ExamAssessmentService:
    """Implements configurable exam patterns, quizzes, tests, timers, autosave, and scoring."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Exam Patterns (Configurable Versioned Rules)
    # ------------------------------------------------------------------
    async def list_exam_patterns(self) -> list[ExamPatternOut]:
        tracks = await get_exam_tracks_map(self.db)
        rows = list(
            (
                await self.db.scalars(
                    select(ExamPattern).order_by(ExamPattern.effective_year.desc())
                )
            ).all()
        )
        results: list[ExamPatternOut] = []
        for row in rows:
            t_code, t_name = tracks.get(row.exam_track_id, ("CUSTOM", "Custom Track"))
            results.append(
                ExamPatternOut(
                    id=row.id,
                    exam_track_id=row.exam_track_id,
                    exam_track_code=t_code,
                    exam_track_name=t_name,
                    version_label=row.version_label,
                    effective_year=row.effective_year,
                    is_active=row.is_active,
                    rules=ExamPatternRules.model_validate(row.rules_jsonb),
                )
            )
        return results

    async def create_exam_pattern(
        self, payload: ExamPatternCreate, caller: AuthenticatedUser
    ) -> ExamPatternOut:
        tracks = await get_exam_tracks_map(self.db)
        if payload.exam_track_id not in tracks:
            raise AppError(
                status_code=404, code="EXAM_TRACK_NOT_FOUND", message="Exam track missing."
            )

        pattern = ExamPattern(
            exam_track_id=payload.exam_track_id,
            version_label=payload.version_label.strip(),
            effective_year=payload.effective_year,
            is_active=payload.is_active,
            rules_jsonb=payload.rules.model_dump(),
        )
        self.db.add(pattern)
        await self.db.flush()
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="assessment.exam_pattern_created",
            resource_type="exam_pattern",
            resource_id=str(pattern.id),
            metadata={"version_label": pattern.version_label},
        )
        await self.db.commit()
        t_code, t_name = tracks[payload.exam_track_id]
        return ExamPatternOut(
            id=pattern.id,
            exam_track_id=pattern.exam_track_id,
            exam_track_code=t_code,
            exam_track_name=t_name,
            version_label=pattern.version_label,
            effective_year=pattern.effective_year,
            is_active=pattern.is_active,
            rules=payload.rules,
        )

    # ------------------------------------------------------------------
    # Dynamic & Teacher Quizzes
    # ------------------------------------------------------------------
    async def generate_quiz(
        self, payload: QuizGenerateRequest, caller: AuthenticatedUser
    ) -> QuizOut:
        if payload.quiz_type in {"teacher", "institution", "competition"} and not (
            caller.has_permission("assessment:create")
            or caller.has_role("teacher")
            or caller.has_role("platform_admin")
            or caller.has_role("content_admin")
        ):
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Creating teacher/institution quizzes requires educator privileges.",
            )

        scoring_rule = payload.scoring_rule
        duration_seconds = payload.duration_seconds
        grace_seconds = payload.grace_seconds
        shuffle_q = payload.shuffle_questions
        shuffle_opt = payload.shuffle_options

        if payload.exam_pattern_id is not None:
            pat = await self.db.get(ExamPattern, payload.exam_pattern_id)
            if pat is None:
                raise AppError(
                    status_code=404, code="PATTERN_NOT_FOUND", message="Pattern missing."
                )
            rules = ExamPatternRules.model_validate(pat.rules_jsonb)
            if duration_seconds is None and rules.duration_seconds is not None:
                duration_seconds = rules.duration_seconds
            grace_seconds = rules.grace_seconds
            if rules.sections:
                scoring_rule = rules.sections[0].scoring

        selected = await select_questions_for_assessment(
            self.db,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
            difficulty_distribution=payload.difficulty_distribution or None,
            question_type_distribution=payload.question_type_distribution or None,
            limit=payload.question_count,
            seed=payload.seed,
            shuffle=shuffle_q,
        )
        if not selected:
            raise AppError(
                status_code=422,
                code="NO_PUBLISHED_QUESTIONS",
                message="No PUBLISHED questions matched the requested quiz filters.",
            )

        quiz = Quiz(
            tenant_id=caller.tenant_id,
            quiz_type=payload.quiz_type,
            title=payload.title.strip(),
            created_by=caller.id,
            exam_pattern_id=payload.exam_pattern_id,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
            config_jsonb={
                "duration_seconds": duration_seconds,
                "grace_seconds": grace_seconds,
                "shuffle_questions": shuffle_q,
                "shuffle_options": shuffle_opt,
                "scoring_rule": scoring_rule.model_dump(),
                "seed": payload.seed,
            },
            is_ai_generated=(payload.quiz_type == "ai_generated"),
            status="PUBLISHED",
        )
        self.db.add(quiz)
        await self.db.flush()

        for seq, pq in enumerate(selected, start=1):
            self.db.add(
                QuizQuestion(
                    quiz_id=quiz.id,
                    sequence_no=seq,
                    question_id=pq.question_id,
                    question_version_id=pq.question_version_id,
                    marks_override=Decimal(str(scoring_rule.correct_marks)),
                    negative_marks_override=Decimal(str(abs(scoring_rule.wrong_marks))),
                )
            )
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="quiz.generated",
            resource_type="quiz",
            resource_id=str(quiz.id),
            metadata={"quiz_type": payload.quiz_type, "question_count": len(selected)},
        )
        await self.db.commit()
        await self.db.refresh(quiz)
        return QuizOut(
            id=quiz.id,
            quiz_type=quiz.quiz_type,
            title=quiz.title,
            status=quiz.status,
            question_count=len(selected),
            duration_seconds=duration_seconds,
            shuffle_questions=shuffle_q,
            is_ai_generated=quiz.is_ai_generated,
            created_at=quiz.created_at,
        )

    async def list_quizzes(self, caller: AuthenticatedUser) -> list[QuizOut]:
        rows = list(
            (
                await self.db.scalars(
                    select(Quiz)
                    .where(
                        (Quiz.created_by == caller.id)
                        | (Quiz.quiz_type.in_(["teacher", "daily", "diagnostic", "competition"]))
                    )
                    .order_by(Quiz.created_at.desc())
                    .limit(50)
                )
            ).all()
        )
        out: list[QuizOut] = []
        for q in rows:
            cnt = int(
                await self.db.scalar(
                    select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_id == q.id)
                )
                or 0
            )
            out.append(
                QuizOut(
                    id=q.id,
                    quiz_type=q.quiz_type,
                    title=q.title,
                    status=q.status,
                    question_count=cnt,
                    duration_seconds=q.config_jsonb.get("duration_seconds"),
                    shuffle_questions=bool(q.config_jsonb.get("shuffle_questions", False)),
                    is_ai_generated=q.is_ai_generated,
                    created_at=q.created_at,
                )
            )
        return out

    # ------------------------------------------------------------------
    # Exam Templates / Tests Management
    # ------------------------------------------------------------------
    async def create_test(self, payload: TestCreateRequest, caller: AuthenticatedUser) -> TestOut:
        test = AssessmentTemplate(
            tenant_id=caller.tenant_id,
            exam_pattern_id=payload.exam_pattern_id,
            title=payload.title.strip(),
            description=payload.description,
            test_category=payload.test_category,
            duration_seconds=payload.duration_seconds,
            grace_seconds=payload.grace_seconds,
            retake_policy_jsonb={"max_attempts": payload.max_attempts, "cooldown_minutes": 0},
            shuffle_questions=payload.shuffle_questions,
            shuffle_options=payload.shuffle_options,
            created_by=caller.id,
            status="DRAFT",
        )
        self.db.add(test)
        await self.db.flush()

        total_max_marks = 0.0
        sections_out: list[TestSectionOut] = []

        for s_seq, sec_in in enumerate(payload.sections, start=1):
            sec = TestSection(
                test_id=test.id,
                sequence_no=s_seq,
                name=sec_in.name,
                subject_id=sec_in.subject_id,
                marking_rule_jsonb=sec_in.scoring_rule.model_dump(),
                attempt_limit=sec_in.attempt_limit,
            )
            self.db.add(sec)
            await self.db.flush()

            selected: list[PinnedQuestionContract]
            if sec_in.explicit_question_ids:
                all_matching = await select_questions_for_assessment(
                    self.db,
                    subject_id=sec_in.subject_id,
                    limit=200,
                    shuffle=False,
                )
                id_set = set(sec_in.explicit_question_ids)
                by_qid = {pq.question_id: pq for pq in all_matching if pq.question_id in id_set}
                selected = [by_qid[qid] for qid in sec_in.explicit_question_ids if qid in by_qid]
            else:
                selected = await select_questions_for_assessment(
                    self.db,
                    subject_id=sec_in.subject_id,
                    chapter_id=sec_in.chapter_id,
                    topic_id=sec_in.topic_id,
                    concept_id=sec_in.concept_id,
                    allowed_question_types=sec_in.allowed_question_types or None,
                    difficulty_distribution=sec_in.difficulty_distribution or None,
                    question_type_distribution=sec_in.question_type_distribution or None,
                    limit=sec_in.question_count,
                    shuffle=payload.shuffle_questions,
                )

            if not selected:
                raise AppError(
                    status_code=422,
                    code="SECTION_HAS_NO_QUESTIONS",
                    message=f"Section '{sec_in.name}' matched zero PUBLISHED questions.",
                )

            for q_seq, pq in enumerate(selected, start=1):
                self.db.add(
                    TestQuestion(
                        test_id=test.id,
                        section_id=sec.id,
                        question_id=pq.question_id,
                        question_version_id=pq.question_version_id,
                        sequence_no=q_seq,
                        marks_override=Decimal(str(sec_in.scoring_rule.correct_marks)),
                        negative_marks_override=Decimal(str(abs(sec_in.scoring_rule.wrong_marks))),
                    )
                )

            effective_count = (
                min(len(selected), sec_in.attempt_limit) if sec_in.attempt_limit else len(selected)
            )
            total_max_marks += effective_count * sec_in.scoring_rule.correct_marks
            sections_out.append(
                TestSectionOut(
                    id=sec.id,
                    sequence_no=sec.sequence_no,
                    name=sec.name,
                    attempt_limit=sec.attempt_limit,
                    question_count=len(selected),
                    marking_rule=sec_in.scoring_rule,
                )
            )

        test.total_marks = Decimal(str(round(total_max_marks, 2)))
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="assessment.test_created",
            resource_type="test",
            resource_id=str(test.id),
            metadata={"total_marks": total_max_marks, "sections": len(sections_out)},
        )
        await self.db.commit()
        await self.db.refresh(test)
        return TestOut(
            id=test.id,
            title=test.title,
            description=test.description,
            test_category=test.test_category,
            exam_pattern_id=test.exam_pattern_id,
            duration_seconds=test.duration_seconds,
            grace_seconds=test.grace_seconds,
            total_marks=float(test.total_marks),
            status=test.status,
            sections=sections_out,
            created_at=test.created_at,
        )

    async def publish_test(self, test_id: UUID, caller: AuthenticatedUser) -> TestOut:
        test = await self.db.get(AssessmentTemplate, test_id)
        if test is None:
            raise AppError(status_code=404, code="TEST_NOT_FOUND", message="Test not found.")
        test.status = "PUBLISHED"
        test.published_at = datetime.now(UTC)
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="assessment.test_published",
            resource_type="test",
            resource_id=str(test.id),
        )
        await self.db.commit()
        return await self._serialize_test(test)

    async def _serialize_test(self, test: AssessmentTemplate) -> TestOut:
        secs = list(
            (
                await self.db.scalars(
                    select(TestSection)
                    .where(TestSection.test_id == test.id)
                    .order_by(TestSection.sequence_no)
                )
            ).all()
        )
        sec_out: list[TestSectionOut] = []
        for s in secs:
            q_cnt = int(
                await self.db.scalar(
                    select(func.count(TestQuestion.id)).where(TestQuestion.section_id == s.id)
                )
                or 0
            )
            sec_out.append(
                TestSectionOut(
                    id=s.id,
                    sequence_no=s.sequence_no,
                    name=s.name,
                    attempt_limit=s.attempt_limit,
                    question_count=q_cnt,
                    marking_rule=ScoringRule.model_validate(s.marking_rule_jsonb),
                )
            )
        return TestOut(
            id=test.id,
            title=test.title,
            description=test.description,
            test_category=test.test_category,
            exam_pattern_id=test.exam_pattern_id,
            duration_seconds=test.duration_seconds,
            grace_seconds=test.grace_seconds,
            total_marks=float(test.total_marks),
            status=test.status,
            sections=sec_out,
            created_at=test.created_at,
        )

    async def list_tests(self, caller: AuthenticatedUser) -> list[TestOut]:
        can_manage = caller.has_permission("assessment:create") and (
            not caller.requires_mfa or caller.mfa_verified
        )
        stmt = select(AssessmentTemplate)
        if not can_manage:
            stmt = stmt.where(AssessmentTemplate.status == "PUBLISHED")
        rows = list(
            (await self.db.scalars(stmt.order_by(AssessmentTemplate.created_at.desc()))).all()
        )
        return [await self._serialize_test(t) for t in rows]

    # ------------------------------------------------------------------
    # Server-Authoritative Attempts, Recovery, Autosave, Submit, Result
    # ------------------------------------------------------------------
    async def start_quiz_attempt(
        self, quiz_id: UUID, caller: AuthenticatedUser
    ) -> AttemptStateResponse:
        quiz = await self.db.get(Quiz, quiz_id)
        if quiz is None or quiz.status != "PUBLISHED":
            raise AppError(status_code=404, code="QUIZ_NOT_FOUND", message="Quiz not found.")

        q_rows = list(
            (
                await self.db.scalars(
                    select(QuizQuestion)
                    .where(QuizQuestion.quiz_id == quiz.id)
                    .order_by(QuizQuestion.sequence_no)
                )
            ).all()
        )
        if not q_rows:
            raise AppError(status_code=422, code="EMPTY_QUIZ", message="Quiz has no questions.")

        cfg = quiz.config_jsonb
        scoring_rule = ScoringRule.model_validate(cfg.get("scoring_rule", {}))
        dur = cfg.get("duration_seconds")
        grace = int(cfg.get("grace_seconds", 15))
        shuffle_q = bool(cfg.get("shuffle_questions", False))

        seed = random.SystemRandom().randint(1, 2_000_000)
        ordered = list(q_rows)
        if shuffle_q:
            # Deterministic seed stored on AssessmentAttempt for audit/replay (non-crypto)
            random.Random(seed).shuffle(ordered)  # noqa: S311

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=int(dur)) if dur else None
        grace_until = expires_at + timedelta(seconds=grace) if expires_at else None

        order_manifest: list[dict[str, Any]] = [
            {
                "sequence_no": idx,
                "section_id": None,
                "section_name": quiz.title,
                "question_version_id": str(qq.question_version_id),
                "scoring_rule": scoring_rule.model_dump(),
            }
            for idx, qq in enumerate(ordered, start=1)
        ]

        attempt = AssessmentAttempt(
            tenant_id=caller.tenant_id,
            student_id=caller.id,
            quiz_id=quiz.id,
            status="in_progress",
            started_at=now,
            expires_at=expires_at,
            grace_until=grace_until,
            seed=seed,
            question_order_jsonb=order_manifest,
        )
        self.db.add(attempt)
        await self.db.flush()

        for item in order_manifest:
            self.db.add(
                AttemptAnswer(
                    attempt_id=attempt.id,
                    question_version_id=UUID(str(item["question_version_id"])),
                    sequence_no=int(item["sequence_no"]),
                    section_id=None,
                    response_jsonb={},
                )
            )
        await self.db.commit()
        return await self.get_attempt_state(attempt.id, caller)

    async def start_test_attempt(
        self, test_id: UUID, caller: AuthenticatedUser
    ) -> AttemptStateResponse:
        test = await self.db.get(AssessmentTemplate, test_id)
        if test is None or test.status != "PUBLISHED":
            raise AppError(status_code=404, code="TEST_NOT_FOUND", message="Test not found.")

        max_attempts = test.retake_policy_jsonb.get("max_attempts")
        if max_attempts is not None:
            prior_count = int(
                await self.db.scalar(
                    select(func.count(AssessmentAttempt.id)).where(
                        AssessmentAttempt.test_id == test.id,
                        AssessmentAttempt.student_id == caller.id,
                    )
                )
                or 0
            )
            if prior_count >= int(max_attempts):
                raise AppError(
                    status_code=403,
                    code="MAX_RETAKES_REACHED",
                    message=f"Maximum allowed attempts ({max_attempts}) reached.",
                )

        sections = list(
            (
                await self.db.scalars(
                    select(TestSection)
                    .where(TestSection.test_id == test.id)
                    .order_by(TestSection.sequence_no)
                )
            ).all()
        )
        seed = random.SystemRandom().randint(1, 2_000_000)
        # Deterministic seed stored on AssessmentAttempt for audit/replay (non-crypto)
        rng = random.Random(seed)  # noqa: S311
        order_manifest: list[dict[str, Any]] = []
        seq_counter = 1

        for sec in sections:
            t_qs = list(
                (
                    await self.db.scalars(
                        select(TestQuestion)
                        .where(TestQuestion.section_id == sec.id)
                        .order_by(TestQuestion.sequence_no)
                    )
                ).all()
            )
            if test.shuffle_questions:
                rng.shuffle(t_qs)
            sec_rule = ScoringRule.model_validate(sec.marking_rule_jsonb)
            for tq in t_qs:
                order_manifest.append(
                    {
                        "sequence_no": seq_counter,
                        "section_id": str(sec.id),
                        "section_name": sec.name,
                        "attempt_limit": sec.attempt_limit,
                        "question_version_id": str(tq.question_version_id),
                        "scoring_rule": sec_rule.model_dump(),
                    }
                )
                seq_counter += 1

        now = datetime.now(UTC)
        expires_at = (
            now + timedelta(seconds=test.duration_seconds) if test.duration_seconds else None
        )
        grace_until = expires_at + timedelta(seconds=test.grace_seconds) if expires_at else None

        attempt = AssessmentAttempt(
            tenant_id=caller.tenant_id,
            student_id=caller.id,
            test_id=test.id,
            status="in_progress",
            started_at=now,
            expires_at=expires_at,
            grace_until=grace_until,
            seed=seed,
            question_order_jsonb=order_manifest,
        )
        self.db.add(attempt)
        await self.db.flush()

        for item in order_manifest:
            self.db.add(
                AttemptAnswer(
                    attempt_id=attempt.id,
                    question_version_id=UUID(item["question_version_id"]),
                    sequence_no=item["sequence_no"],
                    section_id=UUID(item["section_id"]) if item["section_id"] else None,
                    response_jsonb={},
                )
            )
        await self.db.commit()
        return await self.get_attempt_state(attempt.id, caller)

    async def _load_attempt_and_title(
        self, attempt_id: UUID, caller: AuthenticatedUser, *, lock: bool = False
    ) -> tuple[AssessmentAttempt, str, str]:
        stmt = select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id)
        if lock:
            stmt = stmt.with_for_update()
        attempt = await self.db.scalar(stmt)
        if attempt is None or attempt.student_id != caller.id:
            raise AppError(status_code=404, code="ATTEMPT_NOT_FOUND", message="Attempt not found.")

        if attempt.test_id is not None:
            test = await self.db.get(AssessmentTemplate, attempt.test_id)
            return attempt, (test.title if test else "Assessment"), "test"
        quiz = await self.db.get(Quiz, attempt.quiz_id)
        return attempt, (quiz.title if quiz else "Quiz"), "quiz"

    async def _score_and_finalize(
        self,
        *,
        attempt: AssessmentAttempt,
        target_status: str,
        idempotency_key: str | None,
        now: datetime,
    ) -> None:
        answers = list(
            (
                await self.db.scalars(
                    select(AttemptAnswer)
                    .where(AttemptAnswer.attempt_id == attempt.id)
                    .order_by(AttemptAnswer.sequence_no)
                )
            ).all()
        )
        ans_by_qv = {a.question_version_id: a for a in answers}
        manifest = attempt.question_order_jsonb
        version_ids = [UUID(m["question_version_id"]) for m in manifest]
        pinned_map = await get_pinned_versions_map(self.db, version_ids)

        raw_score = 0.0
        max_score = 0.0
        correct_cnt = 0
        wrong_cnt = 0
        unanswered_cnt = 0
        section_buckets: dict[str, dict[str, Any]] = {}

        for item in manifest:
            qv_id = UUID(item["question_version_id"])
            pq = pinned_map[qv_id]
            ans_row = ans_by_qv[qv_id]
            rule = ScoringRule.model_validate(item.get("scoring_rule", {}))
            sec_key = item.get("section_id") or "default"
            sec_name = item.get("section_name") or "General"
            attempt_limit = item.get("attempt_limit")

            bucket = section_buckets.setdefault(
                sec_key,
                {
                    "section_id": item.get("section_id"),
                    "section_name": sec_name,
                    "attempt_limit": attempt_limit,
                    "total_questions": 0,
                    "attempted": 0,
                    "correct": 0,
                    "wrong": 0,
                    "raw_score": 0.0,
                    "max_score": 0.0,
                },
            )
            bucket["total_questions"] += 1

            over_limit = (
                attempt_limit is not None
                and bucket["attempted"] >= int(attempt_limit)
                and not is_response_empty(pq.question_type, ans_row.response_jsonb)
            )
            if over_limit:
                ans_row.is_correct = False
                ans_row.marks_awarded = Decimal("0.00")
                unanswered_cnt += 1
                continue

            evaluated = evaluate_question_with_rule(
                question_type=pq.question_type,
                correct_answer_jsonb=pq.correct_answer_jsonb,
                response_jsonb=ans_row.response_jsonb,
                rule=rule,
            )
            ans_row.is_correct = evaluated.is_correct
            ans_row.marks_awarded = Decimal(str(round(evaluated.marks_awarded, 2)))
            raw_score += evaluated.marks_awarded
            bucket["raw_score"] += evaluated.marks_awarded

            if evaluated.attempted:
                bucket["attempted"] += 1
                if evaluated.is_correct:
                    correct_cnt += 1
                    bucket["correct"] += 1
                else:
                    wrong_cnt += 1
                    bucket["wrong"] += 1
            else:
                unanswered_cnt += 1

        # Compute authoritative section/total max_score respecting optional attempt_limit caps
        for sec_data in section_buckets.values():
            cap = sec_data["attempt_limit"]
            q_cnt = sec_data["total_questions"]
            effective_qs = min(q_cnt, int(cap)) if cap else q_cnt
            first_match = next(
                (
                    m
                    for m in manifest
                    if (m.get("section_id") or "default") == (sec_data["section_id"] or "default")
                ),
                None,
            )
            sec_rule = ScoringRule.model_validate(
                first_match.get("scoring_rule", {}) if first_match else {}
            )
            sec_max = effective_qs * float(sec_rule.correct_marks)
            sec_data["max_score"] = round(sec_max, 2)
            sec_data["raw_score"] = round(sec_data["raw_score"], 2)
            max_score += sec_max

        total_attempted = correct_cnt + wrong_cnt
        accuracy_pct = round((correct_cnt / total_attempted) * 100.0, 2) if total_attempted else 0.0

        attempt.status = target_status
        attempt.submitted_at = now
        if idempotency_key:
            attempt.submission_idempotency_key = idempotency_key
        attempt.raw_score = Decimal(str(round(raw_score, 2)))
        attempt.max_score = Decimal(str(round(max_score, 2)))
        attempt.accuracy_pct = Decimal(str(accuracy_pct))
        attempt.result_summary_jsonb = {
            "correct_count": correct_cnt,
            "wrong_count": wrong_cnt,
            "unanswered_count": unanswered_cnt,
            "sections": [
                {k: v for k, v in sec_data.items() if k != "attempt_limit"}
                for sec_data in section_buckets.values()
            ],
        }

        self.db.add(
            OutboxEvent(
                tenant_id=attempt.tenant_id,
                aggregate_type="assessment_attempt",
                aggregate_id=str(attempt.id),
                topic="assessment.attempt_submitted",
                idempotency_key=f"assessment_submit:{attempt.id}",
                payload_jsonb={
                    "student_id": str(attempt.student_id),
                    "attempt_id": str(attempt.id),
                    "raw_score": round(raw_score, 2),
                    "max_score": round(max_score, 2),
                    "accuracy_pct": accuracy_pct,
                    "correct_count": correct_cnt,
                    "wrong_count": wrong_cnt,
                },
                status="pending",
                available_at=now,
            )
        )

    async def get_attempt_state(
        self, attempt_id: UUID, caller: AuthenticatedUser
    ) -> AttemptStateResponse:
        attempt, title, kind = await self._load_attempt_and_title(attempt_id, caller)
        now = datetime.now(UTC)

        # Auto-finalize if timer expired past grace window
        if (
            attempt.status == "in_progress"
            and attempt.grace_until is not None
            and now > _ensure_utc(attempt.grace_until)
        ):
            locked, _, _ = await self._load_attempt_and_title(attempt_id, caller, lock=True)
            if locked.status == "in_progress":
                await self._score_and_finalize(
                    attempt=locked,
                    target_status="auto_submitted",
                    idempotency_key=f"auto:{locked.id}",
                    now=now,
                )
                await self.db.commit()
                attempt = locked

        answers = list(
            (
                await self.db.scalars(
                    select(AttemptAnswer)
                    .where(AttemptAnswer.attempt_id == attempt.id)
                    .order_by(AttemptAnswer.sequence_no)
                )
            ).all()
        )
        ans_by_qv = {a.question_version_id: a for a in answers}
        manifest = attempt.question_order_jsonb
        pinned_map = await get_pinned_versions_map(
            self.db, [UUID(m["question_version_id"]) for m in manifest]
        )

        questions_out: list[AttemptQuestionStateItem] = []
        for item in manifest:
            qv_id = UUID(item["question_version_id"])
            pq = pinned_map[qv_id]
            ans = ans_by_qv[qv_id]
            rule = ScoringRule.model_validate(item.get("scoring_rule", {}))
            questions_out.append(
                AttemptQuestionStateItem(
                    sequence_no=item["sequence_no"],
                    section_id=UUID(item["section_id"]) if item.get("section_id") else None,
                    section_name=item.get("section_name"),
                    question_id=pq.question_id,
                    question_version_id=pq.question_version_id,
                    question_type=pq.question_type,
                    stem_markdown=pq.stem_markdown,
                    difficulty=pq.difficulty,
                    marks=float(rule.correct_marks),
                    negative_marks=float(rule.wrong_marks),
                    options=[
                        AttemptQuestionOptionView(option_key=k, content_markdown=text)
                        for k, text, _ in pq.options
                    ],
                    response_jsonb=ans.response_jsonb,
                    is_visited=ans.is_visited,
                    is_marked_for_review=ans.is_marked_for_review,
                    time_spent_seconds=ans.time_spent_seconds,
                )
            )

        remaining: int | None = None
        if attempt.expires_at is not None:
            remaining = max(0, int((_ensure_utc(attempt.expires_at) - now).total_seconds()))

        return AttemptStateResponse(
            attempt_id=attempt.id,
            title=title,
            source_kind="test" if kind == "test" else "quiz",
            status=attempt.status,
            started_at=_ensure_utc(attempt.started_at),
            expires_at=_ensure_utc(attempt.expires_at) if attempt.expires_at else None,
            grace_until=_ensure_utc(attempt.grace_until) if attempt.grace_until else None,
            server_now_utc=now,
            remaining_seconds=remaining,
            questions=questions_out,
        )

    async def autosave_answers(
        self,
        attempt_id: UUID,
        payload: AutosaveAnswersRequest,
        caller: AuthenticatedUser,
    ) -> AutosaveResponse:
        attempt, _, _ = await self._load_attempt_and_title(attempt_id, caller, lock=True)
        now = datetime.now(UTC)

        if attempt.status != "in_progress":
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="ATTEMPT_ALREADY_SUBMITTED",
                message="Cannot save answers after submission.",
            )
        if attempt.grace_until is not None and now > _ensure_utc(attempt.grace_until):
            await self._score_and_finalize(
                attempt=attempt,
                target_status="auto_submitted",
                idempotency_key=f"auto:{attempt.id}",
                now=now,
            )
            await self.db.commit()
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="ASSESSMENT_TIME_EXPIRED",
                message="Assessment timer expired past grace window; autosaved answers finalized.",
            )

        answers = list(
            (
                await self.db.scalars(
                    select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
                )
            ).all()
        )
        ans_by_qv = {a.question_version_id: a for a in answers}
        saved = 0
        for upd in payload.answers:
            row = ans_by_qv.get(upd.question_version_id)
            if row is None:
                continue
            row.response_jsonb = upd.response_jsonb
            row.is_visited = upd.is_visited
            row.is_marked_for_review = upd.is_marked_for_review
            row.time_spent_seconds = upd.time_spent_seconds
            row.last_saved_at = now
            saved += 1

        await self.db.commit()
        remaining = (
            max(0, int((_ensure_utc(attempt.expires_at) - now).total_seconds()))
            if attempt.expires_at
            else None
        )
        return AutosaveResponse(
            attempt_id=attempt.id,
            saved_count=saved,
            server_now_utc=now,
            remaining_seconds=remaining,
        )

    async def submit_attempt(
        self,
        attempt_id: UUID,
        payload: SubmitAttemptRequest,
        caller: AuthenticatedUser,
        *,
        idempotency_key: str | None,
    ) -> AttemptResultResponse:
        attempt, _, _ = await self._load_attempt_and_title(attempt_id, caller, lock=True)
        now = datetime.now(UTC)

        # Idempotent replay if already finalized (covers concurrent duplicate submits)
        if attempt.status in {"submitted", "auto_submitted", "graded"}:
            return await self.get_attempt_result(attempt.id, caller)

        if attempt.grace_until is not None and now > _ensure_utc(attempt.grace_until):
            # Auto-finalize using ONLY pre-expiry autosaved answers, reject late submit payload!
            await self._score_and_finalize(
                attempt=attempt,
                target_status="auto_submitted",
                idempotency_key=f"auto:{attempt.id}",
                now=now,
            )
            await self.db.commit()
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="ASSESSMENT_TIME_EXPIRED",
                message="The submission window for this assessment has closed.",
            )

        if payload.answers:
            answers = list(
                (
                    await self.db.scalars(
                        select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
                    )
                ).all()
            )
            ans_by_qv = {a.question_version_id: a for a in answers}
            for upd in payload.answers:
                row = ans_by_qv.get(upd.question_version_id)
                if row is not None:
                    row.response_jsonb = upd.response_jsonb
                    row.is_visited = upd.is_visited
                    row.is_marked_for_review = upd.is_marked_for_review
                    row.time_spent_seconds = upd.time_spent_seconds
                    row.last_saved_at = now

        await self._score_and_finalize(
            attempt=attempt,
            target_status="submitted",
            idempotency_key=idempotency_key or f"submit:{attempt.id}",
            now=now,
        )
        await self.db.commit()
        return await self.get_attempt_result(attempt.id, caller)

    async def get_attempt_result(
        self, attempt_id: UUID, caller: AuthenticatedUser
    ) -> AttemptResultResponse:
        attempt, title, kind = await self._load_attempt_and_title(attempt_id, caller)
        if attempt.status == "in_progress":
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="RESULT_LOCKED_WHILE_IN_PROGRESS",
                message="Results and solutions remain locked until submission.",
            )

        answers = list(
            (
                await self.db.scalars(
                    select(AttemptAnswer)
                    .where(AttemptAnswer.attempt_id == attempt.id)
                    .order_by(AttemptAnswer.sequence_no)
                )
            ).all()
        )
        ans_by_qv = {a.question_version_id: a for a in answers}
        manifest = attempt.question_order_jsonb
        pinned_map = await get_pinned_versions_map(
            self.db, [UUID(m["question_version_id"]) for m in manifest]
        )

        items_out: list[AttemptResultQuestionItem] = []
        for item in manifest:
            qv_id = UUID(item["question_version_id"])
            pq = pinned_map[qv_id]
            ans = ans_by_qv[qv_id]
            items_out.append(
                AttemptResultQuestionItem(
                    sequence_no=item["sequence_no"],
                    section_name=item.get("section_name"),
                    question_id=pq.question_id,
                    question_version_id=pq.question_version_id,
                    question_type=pq.question_type,
                    stem_markdown=pq.stem_markdown,
                    options=[
                        AttemptQuestionOptionView(option_key=k, content_markdown=text)
                        for k, text, _ in pq.options
                    ],
                    student_response_jsonb=ans.response_jsonb,
                    correct_answer_jsonb=pq.correct_answer_jsonb,
                    is_visited=ans.is_visited,
                    is_marked_for_review=ans.is_marked_for_review,
                    time_spent_seconds=ans.time_spent_seconds,
                    is_correct=bool(ans.is_correct),
                    marks_awarded=float(ans.marks_awarded or 0.0),
                    explanation_markdown=pq.explanation_markdown,
                    steps=list(pq.steps),
                    common_mistakes_markdown=pq.common_mistakes_markdown,
                )
            )

        summary = attempt.result_summary_jsonb
        return AttemptResultResponse(
            attempt_id=attempt.id,
            title=title,
            source_kind="test" if kind == "test" else "quiz",
            status=attempt.status,
            raw_score=float(attempt.raw_score or 0.0),
            max_score=float(attempt.max_score or 0.0),
            accuracy_pct=float(attempt.accuracy_pct or 0.0),
            correct_count=int(summary.get("correct_count", 0)),
            wrong_count=int(summary.get("wrong_count", 0)),
            unanswered_count=int(summary.get("unanswered_count", 0)),
            started_at=_ensure_utc(attempt.started_at),
            submitted_at=_ensure_utc(attempt.submitted_at) if attempt.submitted_at else None,
            section_breakdown=[SectionScoreSummary(**s) for s in summary.get("sections", [])],
            items=items_out,
        )

    async def list_attempt_history(self, caller: AuthenticatedUser) -> list[AttemptHistoryItem]:
        rows = list(
            (
                await self.db.scalars(
                    select(AssessmentAttempt)
                    .where(AssessmentAttempt.student_id == caller.id)
                    .order_by(AssessmentAttempt.started_at.desc())
                    .limit(50)
                )
            ).all()
        )
        out: list[AttemptHistoryItem] = []
        for a in rows:
            title = "Assessment"
            kind: Literal["quiz", "test"] = "quiz"
            if a.test_id is not None:
                t = await self.db.get(AssessmentTemplate, a.test_id)
                title = t.title if t else "Assessment"
                kind = "test"
            elif a.quiz_id is not None:
                q = await self.db.get(Quiz, a.quiz_id)
                title = q.title if q else "Quiz"
            out.append(
                AttemptHistoryItem(
                    attempt_id=a.id,
                    title=title,
                    source_kind=kind,
                    status=a.status,
                    raw_score=float(a.raw_score) if a.raw_score is not None else None,
                    max_score=float(a.max_score) if a.max_score is not None else None,
                    accuracy_pct=float(a.accuracy_pct) if a.accuracy_pct is not None else None,
                    started_at=_ensure_utc(a.started_at),
                    submitted_at=_ensure_utc(a.submitted_at) if a.submitted_at else None,
                )
            )
        return out
