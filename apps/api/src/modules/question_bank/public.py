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
    "PinnedQuestionContract",
    "PracticeQuestionContract",
    "evaluate_practice_response",
    "get_pinned_versions_map",
    "get_question_hint",
    "get_question_solution_after_attempt",
    "imports_router",
    "list_published_questions_for_practice",
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
