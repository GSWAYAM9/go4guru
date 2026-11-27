"""Public contract boundary for question_bank module."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.question_bank.models import (
    Question,
    QuestionHint,
    QuestionOption,
    QuestionProvenance,
    QuestionSolution,
    QuestionVersion,
)
from src.modules.question_bank.router import imports_router, questions_router

MODULE_NAME = "question_bank"
MODULE_PHASE = "Phase 1"
MODULE_STATUS = "IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class PracticeQuestionContract:
    """Published question payload for Practice Engine without exposing internal ORM models."""

    question_id: UUID
    question_version_id: UUID
    question_type: str
    subject_id: UUID
    chapter_id: UUID
    topic_id: UUID | None
    concept_id: UUID | None
    stem_markdown: str
    difficulty: str
    default_marks: float
    options: tuple[tuple[str, str], ...]
    correct_answer_jsonb: dict[str, Any]


async def list_published_questions_for_practice(
    db: AsyncSession,
    *,
    subject_id: UUID | None = None,
    chapter_id: UUID | None = None,
    topic_id: UUID | None = None,
    concept_id: UUID | None = None,
    limit: int = 10,
) -> list[PracticeQuestionContract]:
    """Fetch published questions for a practice session."""
    stmt = (
        select(Question, QuestionVersion)
        .join(QuestionVersion, Question.current_version_id == QuestionVersion.id)
        .where(Question.deleted_at.is_(None), Question.status == "PUBLISHED")
    )
    if subject_id:
        stmt = stmt.where(QuestionVersion.subject_id == subject_id)
    if chapter_id:
        stmt = stmt.where(QuestionVersion.chapter_id == chapter_id)
    if topic_id:
        stmt = stmt.where(QuestionVersion.topic_id == topic_id)
    if concept_id:
        stmt = stmt.where(QuestionVersion.concept_id == concept_id)

    rows = (await db.execute(stmt.order_by(Question.created_at.asc()).limit(limit))).all()
    results: list[PracticeQuestionContract] = []
    for q, qv in rows:
        opts = (
            await db.scalars(
                select(QuestionOption)
                .where(QuestionOption.question_version_id == qv.id)
                .order_by(QuestionOption.option_key)
            )
        ).all()
        results.append(
            PracticeQuestionContract(
                question_id=q.id,
                question_version_id=qv.id,
                question_type=q.question_type,
                subject_id=qv.subject_id,
                chapter_id=qv.chapter_id,
                topic_id=qv.topic_id,
                concept_id=qv.concept_id,
                stem_markdown=qv.stem_markdown,
                difficulty=qv.difficulty,
                default_marks=float(qv.default_marks),
                options=tuple((o.option_key, o.content_markdown) for o in opts),
                correct_answer_jsonb=qv.correct_answer_jsonb,
            )
        )
    return results


async def get_question_hint(
    db: AsyncSession, *, question_version_id: UUID, hint_level: int
) -> str | None:
    """Return graduated hint markdown at the requested level (1..3)."""
    hint = await db.scalar(
        select(QuestionHint).where(
            QuestionHint.question_version_id == question_version_id,
            QuestionHint.hint_level == hint_level,
        )
    )
    return hint.hint_markdown if hint else None


async def get_question_solution_after_attempt(
    db: AsyncSession, *, question_version_id: UUID
) -> tuple[dict[str, Any] | None, str | None, list[str], str | None]:
    """Return answer + verified explanation/steps/mistakes AFTER an attempt is scored."""
    qv = await db.get(QuestionVersion, question_version_id)
    if qv is None:
        return None, None, [], None
    sol = await db.scalar(
        select(QuestionSolution).where(QuestionSolution.question_version_id == qv.id)
    )
    if sol is None:
        return qv.correct_answer_jsonb, None, [], None
    return (
        qv.correct_answer_jsonb,
        sol.explanation_markdown,
        list(sol.steps_jsonb),
        sol.common_mistakes_markdown,
    )


def evaluate_practice_response(
    *,
    question_type: str,
    correct_answer_jsonb: dict[str, Any],
    response_jsonb: dict[str, Any],
    default_marks: float,
) -> tuple[bool, float]:
    """Deterministically grade a student practice attempt against pinned version answer."""
    if question_type in {"mcq_single", "assertion_reason"}:
        expected = str(correct_answer_jsonb.get("correct_key", "")).strip().upper()
        given = str(response_jsonb.get("selected_key", "")).strip().upper()
        is_correct = bool(expected and given == expected)
        return is_correct, default_marks if is_correct else 0.0

    if question_type == "mcq_multiple":
        expected_set = {
            str(k).strip().upper() for k in correct_answer_jsonb.get("correct_keys", [])
        }
        given_set = {str(k).strip().upper() for k in response_jsonb.get("selected_keys", [])}
        is_correct = bool(expected_set and given_set == expected_set)
        return is_correct, default_marks if is_correct else 0.0

    if question_type in {"numerical", "integer"}:
        try:
            expected_val = float(correct_answer_jsonb["expected_value"])
            tol = float(correct_answer_jsonb.get("tolerance_abs", 0.01))
            given_val = float(response_jsonb["numeric_value"])
        except (KeyError, TypeError, ValueError):
            return False, 0.0
        is_correct = abs(given_val - expected_val) <= tol
        return is_correct, default_marks if is_correct else 0.0

    # Subjective short/long answer checked by exact normalized comparison when available
    expected_text = str(correct_answer_jsonb.get("expected_text", "")).strip().lower()
    given_text = str(response_jsonb.get("text_answer", "")).strip().lower()
    is_correct = bool(expected_text and given_text == expected_text)
    return is_correct, default_marks if is_correct else 0.0


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "ExamQuestionAuditStats",
    "ExamQuestionItemContract",
    "PinnedQuestionContract",
    "PracticeQuestionContract",
    "VerifiedPyqProvenanceContract",
    "evaluate_practice_response",
    "get_exam_question_audit_stats",
    "get_pinned_versions_map",
    "get_question_hint",
    "get_question_solution_after_attempt",
    "imports_router",
    "list_published_questions_for_practice",
    "list_questions_for_exam_prep",
    "questions_router",
    "select_questions_for_assessment",
]


@dataclass(frozen=True, slots=True)
class PinnedQuestionContract:
    """Full question snapshot bound to an immutable question_version_id for quizzes/tests."""

    question_id: UUID
    question_version_id: UUID
    question_type: str
    subject_id: UUID
    chapter_id: UUID
    topic_id: UUID | None
    concept_id: UUID | None
    stem_markdown: str
    difficulty: str
    default_marks: float
    default_negative_marks: float
    options: tuple[tuple[str, str, bool], ...]
    correct_answer_jsonb: dict[str, Any]
    explanation_markdown: str | None
    steps: tuple[str, ...]
    common_mistakes_markdown: str | None


async def select_questions_for_assessment(
    db: AsyncSession,
    *,
    subject_id: UUID | None = None,
    chapter_id: UUID | None = None,
    topic_id: UUID | None = None,
    concept_id: UUID | None = None,
    allowed_question_types: list[str] | None = None,
    difficulty_distribution: dict[str, int] | None = None,
    question_type_distribution: dict[str, int] | None = None,
    limit: int = 10,
    seed: int = 42,
    shuffle: bool = True,
) -> list[PinnedQuestionContract]:
    """Select PUBLISHED questions respecting filters, difficulty/type distributions, and seed."""
    stmt = (
        select(Question, QuestionVersion)
        .join(QuestionVersion, Question.current_version_id == QuestionVersion.id)
        .where(Question.deleted_at.is_(None), Question.status == "PUBLISHED")
    )
    if subject_id:
        stmt = stmt.where(QuestionVersion.subject_id == subject_id)
    if chapter_id:
        stmt = stmt.where(QuestionVersion.chapter_id == chapter_id)
    if topic_id:
        stmt = stmt.where(QuestionVersion.topic_id == topic_id)
    if concept_id:
        stmt = stmt.where(QuestionVersion.concept_id == concept_id)
    if allowed_question_types:
        stmt = stmt.where(Question.question_type.in_(allowed_question_types))

    rows = list((await db.execute(stmt.order_by(Question.created_at.asc()))).all())
    # Deterministic seed passed by caller for reproducible quiz ordering (non-crypto)
    rng = random.Random(seed)  # noqa: S311
    if shuffle:
        rng.shuffle(rows)

    chosen: list[tuple[Question, QuestionVersion]] = []
    chosen_ids: set[UUID] = set()

    if question_type_distribution:
        for qtype, count_needed in question_type_distribution.items():
            for q, qv in rows:
                if count_needed <= 0:
                    break
                if q.id not in chosen_ids and q.question_type == qtype:
                    chosen.append((q, qv))
                    chosen_ids.add(q.id)
                    count_needed -= 1

    if difficulty_distribution:
        for diff, count_needed in difficulty_distribution.items():
            for q, qv in rows:
                if count_needed <= 0 or len(chosen) >= limit:
                    break
                if q.id not in chosen_ids and qv.difficulty == diff:
                    chosen.append((q, qv))
                    chosen_ids.add(q.id)
                    count_needed -= 1

    # Fill remaining capacity cleanly up to requested limit
    for q, qv in rows:
        if len(chosen) >= limit:
            break
        if q.id not in chosen_ids:
            chosen.append((q, qv))
            chosen_ids.add(q.id)

    version_ids = [qv.id for _, qv in chosen[:limit]]
    pinned_map = await get_pinned_versions_map(db, version_ids)
    return [pinned_map[vid] for vid in version_ids if vid in pinned_map]


async def get_pinned_versions_map(
    db: AsyncSession, version_ids: list[UUID]
) -> dict[UUID, PinnedQuestionContract]:
    """Load exact pinned QuestionVersion snapshots (never affected by later edits)."""
    if not version_ids:
        return {}
    rows = (
        await db.execute(
            select(Question, QuestionVersion)
            .join(QuestionVersion, QuestionVersion.question_id == Question.id)
            .where(QuestionVersion.id.in_(version_ids))
        )
    ).all()

    opts = (
        await db.scalars(
            select(QuestionOption)
            .where(QuestionOption.question_version_id.in_(version_ids))
            .order_by(QuestionOption.option_key)
        )
    ).all()
    opts_map: dict[UUID, list[tuple[str, str, bool]]] = {}
    for o in opts:
        opts_map.setdefault(o.question_version_id, []).append(
            (o.option_key, o.content_markdown, bool(o.is_correct))
        )

    sols = (
        await db.scalars(
            select(QuestionSolution).where(QuestionSolution.question_version_id.in_(version_ids))
        )
    ).all()
    sol_map: dict[UUID, QuestionSolution] = {}
    for s in sols:
        if s.question_version_id not in sol_map or s.solution_type == "primary":
            sol_map[s.question_version_id] = s

    result: dict[UUID, PinnedQuestionContract] = {}
    for q, qv in rows:
        sol = sol_map.get(qv.id)
        result[qv.id] = PinnedQuestionContract(
            question_id=q.id,
            question_version_id=qv.id,
            question_type=q.question_type,
            subject_id=qv.subject_id,
            chapter_id=qv.chapter_id,
            topic_id=qv.topic_id,
            concept_id=qv.concept_id,
            stem_markdown=qv.stem_markdown,
            difficulty=qv.difficulty,
            default_marks=float(qv.default_marks),
            default_negative_marks=float(qv.default_negative_marks),
            options=tuple(opts_map.get(qv.id, [])),
            correct_answer_jsonb=qv.correct_answer_jsonb,
            explanation_markdown=sol.explanation_markdown if sol else None,
            steps=tuple(sol.steps_jsonb) if sol else (),
            common_mistakes_markdown=sol.common_mistakes_markdown if sol else None,
        )
    return result


# ----------------------------------------------------------------------
# Phase 9: Exam-Specific Verified PYQ & Question-Bank Audit Contracts
# ----------------------------------------------------------------------

EXAM_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "CBSE_BOARD": ("cbse", "cbse board", "cbse class 10", "cbse class 12"),
    "JEE_MAIN": ("jee main", "jee-main", "jee_main"),
    "JEE_ADVANCED": ("jee advanced", "jee-advanced", "jee_advanced", "jee adv"),
    "NEET": ("neet", "neet-ug", "neet ug"),
}


def _provenance_matches_exam(exam_code: str, exam_name: str | None) -> bool:
    if not exam_name:
        return False
    norm = exam_name.strip().lower()
    aliases = EXAM_NAME_ALIASES.get(exam_code.upper(), (exam_code.lower(),))
    if exam_code.upper() == "JEE_MAIN" and "advanced" in norm:
        return False
    if exam_code.upper() == "JEE_ADVANCED" and "main" in norm:
        return False
    return any(alias in norm for alias in aliases)


def _is_strictly_verified_pyq(qv: QuestionVersion, prov: QuestionProvenance | None) -> bool:
    """Enforce zero-fabrication PYQ rule: never label AI or unverified questions as PYQ."""
    if prov is None or not prov.is_pyq:
        return False
    if qv.ai_generated:
        return False
    if (prov.source_type or "").strip().lower() in {"ai_generated", "synthetic", "generated"}:
        return False
    if (prov.verification_status or "").strip().lower() != "verified":
        return False
    if prov.verified_by is None:
        return False
    if not (prov.exam_name and prov.exam_name.strip()):
        return False
    if prov.exam_year is None or not (1980 <= int(prov.exam_year) <= 2035):
        return False
    return True


def _build_verified_pyq_contract(
    qv: QuestionVersion, prov: QuestionProvenance | None
) -> VerifiedPyqProvenanceContract | None:
    if not _is_strictly_verified_pyq(qv, prov) or prov is None:
        return None
    parts = [str(prov.exam_name).strip(), str(prov.exam_year)]
    if prov.exam_session and prov.exam_session.strip():
        parts.append(prov.exam_session.strip())
    if prov.exam_shift and prov.exam_shift.strip():
        parts.append(prov.exam_shift.strip())
    return VerifiedPyqProvenanceContract(
        is_verified_pyq=True,
        badge_label=" · ".join(parts),
        exam_name=str(prov.exam_name).strip(),
        exam_year=int(prov.exam_year),  # type: ignore[arg-type]
        exam_session=prov.exam_session,
        exam_shift=prov.exam_shift,
        paper_code=prov.paper_code,
        question_number=prov.question_number,
        source_url=prov.source_url,
        verification_status="verified",
    )


@dataclass(frozen=True, slots=True)
class VerifiedPyqProvenanceContract:
    """Verified PYQ citation attached ONLY when provenance passes strict verification."""

    is_verified_pyq: bool
    badge_label: str
    exam_name: str
    exam_year: int
    exam_session: str | None
    exam_shift: str | None
    paper_code: str | None
    question_number: str | None
    source_url: str | None
    verification_status: str


@dataclass(frozen=True, slots=True)
class ExamQuestionItemContract:
    """Answer-redacted published question item for Exam Prep explorer & PYQ drill."""

    question_id: UUID
    question_version_id: UUID
    question_type: str
    subject_id: UUID
    chapter_id: UUID
    topic_id: UUID | None
    concept_id: UUID | None
    stem_markdown: str
    difficulty: str
    default_marks: float
    default_negative_marks: float
    estimated_seconds: int
    options: tuple[tuple[str, str], ...]
    pyq_provenance: VerifiedPyqProvenanceContract | None


@dataclass(frozen=True, slots=True)
class ExamQuestionAuditStats:
    """Real audited counts for honest coverage reporting and PYQ filter facets."""

    chapter_published_counts: dict[UUID, int]
    chapter_verified_pyq_counts: dict[UUID, int]
    total_published_questions: int
    total_verified_pyqs: int
    unverified_pyq_excluded_count: int
    available_years: tuple[int, ...]
    available_sessions: tuple[str, ...]
    available_difficulties: tuple[str, ...]
    available_question_types: tuple[str, ...]


async def list_questions_for_exam_prep(
    db: AsyncSession,
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
    chapter_ids_scope: set[UUID] | None = None,
    limit: int = 40,
) -> list[ExamQuestionItemContract]:
    """Return answer-redacted PUBLISHED questions filtered for an exam track.

    When `verified_pyq_only=True`, strictly returns ONLY questions whose provenance
    passes `_is_strictly_verified_pyq` AND matches the requested exam track.
    """
    stmt = (
        select(Question, QuestionVersion, QuestionProvenance)
        .join(QuestionVersion, Question.current_version_id == QuestionVersion.id)
        .outerjoin(QuestionProvenance, QuestionProvenance.question_id == Question.id)
        .where(Question.deleted_at.is_(None), Question.status == "PUBLISHED")
    )
    if difficulty:
        stmt = stmt.where(QuestionVersion.difficulty == difficulty)
    if question_type:
        stmt = stmt.where(Question.question_type == question_type)
    if subject_id:
        stmt = stmt.where(QuestionVersion.subject_id == subject_id)
    if chapter_id:
        stmt = stmt.where(QuestionVersion.chapter_id == chapter_id)
    if topic_id:
        stmt = stmt.where(QuestionVersion.topic_id == topic_id)
    if concept_id:
        stmt = stmt.where(QuestionVersion.concept_id == concept_id)
    if chapter_ids_scope:
        stmt = stmt.where(QuestionVersion.chapter_id.in_(list(chapter_ids_scope)))

    rows = (await db.execute(stmt.order_by(Question.created_at.desc()))).all()
    matched: list[tuple[Question, QuestionVersion, VerifiedPyqProvenanceContract | None]] = []
    for q, qv, prov in rows:
        verified_prov = _build_verified_pyq_contract(qv, prov)
        if verified_prov is not None and not _provenance_matches_exam(exam_code, verified_prov.exam_name):
            # Do not attach another exam's PYQ badge as this exam's PYQ
            verified_prov = None

        if verified_pyq_only and verified_prov is None:
            continue
        if exam_year is not None:
            if verified_prov is None or verified_prov.exam_year != exam_year:
                continue
        if exam_session:
            if verified_prov is None or (verified_prov.exam_session or "").strip().lower() != exam_session.strip().lower():
                continue

        matched.append((q, qv, verified_prov))
        if len(matched) >= limit:
            break

    qv_ids = [qv.id for _, qv, _ in matched]
    opts_map: dict[UUID, list[tuple[str, str]]] = {}
    if qv_ids:
        opts = (
            await db.scalars(
                select(QuestionOption)
                .where(QuestionOption.question_version_id.in_(qv_ids))
                .order_by(QuestionOption.option_key)
            )
        ).all()
        for o in opts:
            # Redact o.is_correct strictly!
            opts_map.setdefault(o.question_version_id, []).append((o.option_key, o.content_markdown))

    return [
        ExamQuestionItemContract(
            question_id=q.id,
            question_version_id=qv.id,
            question_type=q.question_type,
            subject_id=qv.subject_id,
            chapter_id=qv.chapter_id,
            topic_id=qv.topic_id,
            concept_id=qv.concept_id,
            stem_markdown=qv.stem_markdown,
            difficulty=qv.difficulty,
            default_marks=float(qv.default_marks),
            default_negative_marks=float(qv.default_negative_marks),
            estimated_seconds=int(qv.estimated_seconds),
            options=tuple(opts_map.get(qv.id, [])),
            pyq_provenance=vprov,
        )
        for q, qv, vprov in matched
    ]


async def get_exam_question_audit_stats(
    db: AsyncSession,
    *,
    exam_code: str,
    chapter_ids_scope: set[UUID] | None = None,
) -> ExamQuestionAuditStats:
    """Compute honest published question counts, verified PYQ counts, and available facets."""
    stmt = (
        select(Question, QuestionVersion, QuestionProvenance)
        .join(QuestionVersion, Question.current_version_id == QuestionVersion.id)
        .outerjoin(QuestionProvenance, QuestionProvenance.question_id == Question.id)
        .where(Question.deleted_at.is_(None), Question.status == "PUBLISHED")
    )
    rows = (await db.execute(stmt)).all()

    chap_pub: dict[UUID, int] = {}
    chap_pyq: dict[UUID, int] = {}
    total_pub = 0
    total_pyq = 0
    unverified_pyq_excluded = 0
    years: set[int] = set()
    sessions: set[str] = set()
    difficulties: set[str] = set()
    qtypes: set[str] = set()

    for q, qv, prov in rows:
        in_scope = chapter_ids_scope is None or qv.chapter_id in chapter_ids_scope
        vprov = _build_verified_pyq_contract(qv, prov)
        matches_exam_pyq = vprov is not None and _provenance_matches_exam(exam_code, vprov.exam_name)

        if prov is not None and prov.is_pyq and not matches_exam_pyq:
            # Track claimed-but-unverified PYQs matching this exam name (excluded by zero-fabrication guard)
            if _provenance_matches_exam(exam_code, prov.exam_name) and not _is_strictly_verified_pyq(qv, prov):
                unverified_pyq_excluded += 1

        if in_scope or matches_exam_pyq:
            total_pub += 1
            chap_pub[qv.chapter_id] = chap_pub.get(qv.chapter_id, 0) + 1
            difficulties.add(qv.difficulty)
            qtypes.add(q.question_type)

        if matches_exam_pyq and vprov is not None:
            total_pyq += 1
            chap_pyq[qv.chapter_id] = chap_pyq.get(qv.chapter_id, 0) + 1
            years.add(vprov.exam_year)
            if vprov.exam_session and vprov.exam_session.strip():
                sessions.add(vprov.exam_session.strip())

    return ExamQuestionAuditStats(
        chapter_published_counts=chap_pub,
        chapter_verified_pyq_counts=chap_pyq,
        total_published_questions=total_pub,
        total_verified_pyqs=total_pyq,
        unverified_pyq_excluded_count=unverified_pyq_excluded,
        available_years=tuple(sorted(years, reverse=True)),
        available_sessions=tuple(sorted(sessions)),
        available_difficulties=tuple(sorted(difficulties)),
        available_question_types=tuple(sorted(qtypes)),
    )
