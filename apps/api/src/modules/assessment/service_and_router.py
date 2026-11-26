"""Service and HTTP routers for Practice Engine, Notes, and Saved Questions."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.core.errors import AppError
from src.core.outbox import OutboxEvent
from src.modules.assessment.models import (
    PracticeSession,
    QuestionAttempt,
    SavedQuestion,
    StudentNote,
)
from src.modules.assessment.schemas import (
    AttemptResultOut,
    AttemptSubmitRequest,
    BookmarkCreateRequest,
    BookmarkOut,
    HintRevealOut,
    HintRevealRequest,
    PracticeOptionView,
    PracticeQuestionView,
    PracticeSessionCreateRequest,
    PracticeSessionOut,
    StudentNoteCreate,
    StudentNoteOut,
    StudentNoteUpdate,
)
from src.modules.question_bank.public import (
    evaluate_practice_response,
    get_question_hint,
    get_question_solution_after_attempt,
    list_published_questions_for_practice,
)

practice_router = APIRouter(prefix="/api/v1/practice", tags=["practice"])
notes_router = APIRouter(prefix="/api/v1/notes", tags=["notes"])
bookmarks_router = APIRouter(prefix="/api/v1/bookmarks", tags=["bookmarks"])


class PracticeService:
    """Manages student practice sessions, immediate grading, hints, notes, and bookmarks."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def start_session(
        self, payload: PracticeSessionCreateRequest, caller: AuthenticatedUser
    ) -> PracticeSessionOut:
        questions = await list_published_questions_for_practice(
            self.db,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
            limit=payload.limit,
        )
        sess = PracticeSession(
            student_id=caller.id,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
            mode=payload.mode,
            question_ids_jsonb=[str(q.question_id) for q in questions],
            hints_revealed_jsonb={},
        )
        self.db.add(sess)
        await self.db.commit()
        await self.db.refresh(sess)

        return PracticeSessionOut(
            id=sess.id,
            mode=sess.mode,
            subject_id=sess.subject_id,
            chapter_id=sess.chapter_id,
            topic_id=sess.topic_id,
            concept_id=sess.concept_id,
            started_at=sess.started_at,
            ended_at=sess.ended_at,
            questions=[
                PracticeQuestionView(
                    question_id=q.question_id,
                    question_version_id=q.question_version_id,
                    question_type=q.question_type,
                    stem_markdown=q.stem_markdown,
                    difficulty=q.difficulty,
                    default_marks=q.default_marks,
                    options=[
                        PracticeOptionView(option_key=k, content_markdown=text)
                        for k, text in q.options
                    ],
                )
                for q in questions
            ],
            attempts=[],
            hints_revealed={},
        )

    async def get_session(self, session_id: UUID, caller: AuthenticatedUser) -> PracticeSessionOut:
        sess = await self.db.get(PracticeSession, session_id)
        if sess is None or sess.student_id != caller.id:
            raise AppError(status_code=404, code="SESSION_NOT_FOUND", message="Session not found.")

        published = await list_published_questions_for_practice(
            self.db,
            subject_id=sess.subject_id,
            chapter_id=sess.chapter_id,
            topic_id=sess.topic_id,
            concept_id=sess.concept_id,
            limit=50,
        )
        q_by_id = {str(q.question_id): q for q in published}
        ordered_qs = [q_by_id[qid] for qid in sess.question_ids_jsonb if qid in q_by_id]

        attempt_rows = list(
            (
                await self.db.scalars(
                    select(QuestionAttempt)
                    .where(
                        QuestionAttempt.practice_session_id == sess.id,
                        QuestionAttempt.student_id == caller.id,
                    )
                    .order_by(QuestionAttempt.attempted_at)
                )
            ).all()
        )
        attempts_out: list[AttemptResultOut] = []
        for att in attempt_rows:
            ans, expl, steps, mistakes = await get_question_solution_after_attempt(
                self.db, question_version_id=att.question_version_id
            )
            attempts_out.append(
                AttemptResultOut(
                    id=att.id,
                    question_id=att.question_id,
                    question_version_id=att.question_version_id,
                    is_correct=att.is_correct,
                    score_awarded=float(att.score_awarded),
                    hints_used_count=att.hints_used_count,
                    time_spent_seconds=att.time_spent_seconds,
                    attempted_at=att.attempted_at,
                    correct_answer_jsonb=ans,
                    explanation_markdown=expl,
                    steps=steps,
                    common_mistakes_markdown=mistakes,
                )
            )

        return PracticeSessionOut(
            id=sess.id,
            mode=sess.mode,
            subject_id=sess.subject_id,
            chapter_id=sess.chapter_id,
            topic_id=sess.topic_id,
            concept_id=sess.concept_id,
            started_at=sess.started_at,
            ended_at=sess.ended_at,
            questions=[
                PracticeQuestionView(
                    question_id=q.question_id,
                    question_version_id=q.question_version_id,
                    question_type=q.question_type,
                    stem_markdown=q.stem_markdown,
                    difficulty=q.difficulty,
                    default_marks=q.default_marks,
                    options=[
                        PracticeOptionView(option_key=k, content_markdown=text)
                        for k, text in q.options
                    ],
                )
                for q in ordered_qs
            ],
            attempts=attempts_out,
            hints_revealed=dict(sess.hints_revealed_jsonb),
        )

    async def reveal_hint(
        self, session_id: UUID, payload: HintRevealRequest, caller: AuthenticatedUser
    ) -> HintRevealOut:
        sess = await self.db.get(PracticeSession, session_id)
        if sess is None or sess.student_id != caller.id:
            raise AppError(status_code=404, code="SESSION_NOT_FOUND", message="Session not found.")
        q_key = str(payload.question_id)
        if q_key not in sess.question_ids_jsonb:
            raise AppError(
                status_code=404, code="QUESTION_NOT_IN_SESSION", message="Question not in session."
            )

        published = await list_published_questions_for_practice(
            self.db,
            subject_id=sess.subject_id,
            chapter_id=sess.chapter_id,
            topic_id=sess.topic_id,
            concept_id=sess.concept_id,
            limit=50,
        )
        target = next((q for q in published if q.question_id == payload.question_id), None)
        if target is None:
            raise AppError(status_code=404, code="QUESTION_NOT_FOUND", message="Question missing.")

        hint_text = await get_question_hint(
            self.db,
            question_version_id=target.question_version_id,
            hint_level=payload.hint_level,
        )
        hints_map = {k: list(v) for k, v in sess.hints_revealed_jsonb.items()}
        existing_levels = {int(item["hint_level"]) for item in hints_map.get(q_key, [])}
        if hint_text is not None and payload.hint_level not in existing_levels:
            hints_map.setdefault(q_key, []).append(
                {"hint_level": payload.hint_level, "hint_markdown": hint_text}
            )
            sess.hints_revealed_jsonb = hints_map
            await self.db.commit()

        return HintRevealOut(
            question_id=payload.question_id,
            hint_level=payload.hint_level,
            hint_markdown=hint_text,
            hints_used_count=len(hints_map.get(q_key, [])),
        )

    async def submit_attempt(
        self, session_id: UUID, payload: AttemptSubmitRequest, caller: AuthenticatedUser
    ) -> AttemptResultOut:
        sess = await self.db.get(PracticeSession, session_id)
        if sess is None or sess.student_id != caller.id:
            raise AppError(status_code=404, code="SESSION_NOT_FOUND", message="Session not found.")
        q_key = str(payload.question_id)
        if q_key not in sess.question_ids_jsonb:
            raise AppError(
                status_code=404, code="QUESTION_NOT_IN_SESSION", message="Question not in session."
            )

        published = await list_published_questions_for_practice(
            self.db,
            subject_id=sess.subject_id,
            chapter_id=sess.chapter_id,
            topic_id=sess.topic_id,
            concept_id=sess.concept_id,
            limit=50,
        )
        target = next((q for q in published if q.question_id == payload.question_id), None)
        if target is None:
            raise AppError(status_code=404, code="QUESTION_NOT_FOUND", message="Question missing.")

        is_correct, score_awarded = evaluate_practice_response(
            question_type=target.question_type,
            correct_answer_jsonb=target.correct_answer_jsonb,
            response_jsonb=payload.response_jsonb,
            default_marks=target.default_marks,
        )
        hints_used = len(sess.hints_revealed_jsonb.get(q_key, []))

        att = QuestionAttempt(
            student_id=caller.id,
            question_id=target.question_id,
            question_version_id=target.question_version_id,
            practice_session_id=sess.id,
            response_jsonb=payload.response_jsonb,
            is_correct=is_correct,
            score_awarded=Decimal(str(score_awarded)),
            hints_used_count=hints_used,
            time_spent_seconds=payload.time_spent_seconds,
        )
        self.db.add(att)
        await self.db.flush()

        self.db.add(
            OutboxEvent(
                tenant_id=caller.tenant_id,
                aggregate_type="question_attempt",
                aggregate_id=str(att.id),
                topic="learning.question_attempted",
                idempotency_key=f"attempt:{att.id}",
                payload_jsonb={
                    "student_id": str(caller.id),
                    "question_id": str(target.question_id),
                    "concept_id": str(target.concept_id) if target.concept_id else None,
                    "is_correct": is_correct,
                    "hints_used_count": hints_used,
                },
                status="pending",
                available_at=datetime.now(UTC),
            )
        )
        await self.db.commit()
        await self.db.refresh(att)

        ans, expl, steps, mistakes = await get_question_solution_after_attempt(
            self.db, question_version_id=target.question_version_id
        )
        return AttemptResultOut(
            id=att.id,
            question_id=att.question_id,
            question_version_id=att.question_version_id,
            is_correct=att.is_correct,
            score_awarded=float(att.score_awarded),
            hints_used_count=att.hints_used_count,
            time_spent_seconds=att.time_spent_seconds,
            attempted_at=att.attempted_at,
            correct_answer_jsonb=ans,
            explanation_markdown=expl,
            steps=steps,
            common_mistakes_markdown=mistakes,
        )


@practice_router.post(
    "/sessions", response_model=PracticeSessionOut, status_code=status.HTTP_201_CREATED
)
async def start_practice_session(
    payload: PracticeSessionCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("practice:use")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> PracticeSessionOut:
    return await PracticeService(db).start_session(payload, caller)


@practice_router.get("/sessions/{session_id}", response_model=PracticeSessionOut)
async def get_practice_session(
    session_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("practice:use")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> PracticeSessionOut:
    return await PracticeService(db).get_session(session_id, caller)


@practice_router.post("/sessions/{session_id}/hints", response_model=HintRevealOut)
async def reveal_practice_hint(
    session_id: UUID,
    payload: HintRevealRequest,
    caller: AuthenticatedUser = Depends(require_permissions("practice:use")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> HintRevealOut:
    return await PracticeService(db).reveal_hint(session_id, payload, caller)


@practice_router.post("/sessions/{session_id}/attempts", response_model=AttemptResultOut)
async def submit_practice_attempt(
    session_id: UUID,
    payload: AttemptSubmitRequest,
    caller: AuthenticatedUser = Depends(require_permissions("practice:use")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AttemptResultOut:
    return await PracticeService(db).submit_attempt(session_id, payload, caller)


@notes_router.get("", response_model=list[StudentNoteOut])
async def list_my_notes(
    caller: AuthenticatedUser = Depends(require_permissions("notes:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[StudentNoteOut]:
    rows = list(
        (
            await db.scalars(
                select(StudentNote)
                .where(StudentNote.student_id == caller.id)
                .order_by(StudentNote.updated_at.desc())
            )
        ).all()
    )
    return [
        StudentNoteOut(
            id=n.id,
            concept_id=n.concept_id,
            question_id=n.question_id,
            title=n.title,
            body_markdown=n.body_markdown,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in rows
    ]


@notes_router.post("", response_model=StudentNoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: StudentNoteCreate,
    caller: AuthenticatedUser = Depends(require_permissions("notes:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> StudentNoteOut:
    note = StudentNote(
        student_id=caller.id,
        concept_id=payload.concept_id,
        question_id=payload.question_id,
        title=payload.title.strip(),
        body_markdown=payload.body_markdown,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return StudentNoteOut(
        id=note.id,
        concept_id=note.concept_id,
        question_id=note.question_id,
        title=note.title,
        body_markdown=note.body_markdown,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@notes_router.patch("/{note_id}", response_model=StudentNoteOut)
async def update_note(
    note_id: UUID,
    payload: StudentNoteUpdate,
    caller: AuthenticatedUser = Depends(require_permissions("notes:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> StudentNoteOut:
    note = await db.get(StudentNote, note_id)
    if note is None or note.student_id != caller.id:
        raise AppError(status_code=404, code="NOTE_NOT_FOUND", message="Note not found.")
    if payload.title is not None:
        note.title = payload.title.strip()
    if payload.body_markdown is not None:
        note.body_markdown = payload.body_markdown
    await db.commit()
    await db.refresh(note)
    return StudentNoteOut(
        id=note.id,
        concept_id=note.concept_id,
        question_id=note.question_id,
        title=note.title,
        body_markdown=note.body_markdown,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@notes_router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("notes:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> None:
    note = await db.get(StudentNote, note_id)
    if note is None or note.student_id != caller.id:
        raise AppError(status_code=404, code="NOTE_NOT_FOUND", message="Note not found.")
    await db.delete(note)
    await db.commit()


@bookmarks_router.get("", response_model=list[BookmarkOut])
async def list_bookmarks(
    caller: AuthenticatedUser = Depends(require_permissions("notes:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[BookmarkOut]:
    rows = list(
        (
            await db.scalars(
                select(SavedQuestion)
                .where(SavedQuestion.student_id == caller.id)
                .order_by(SavedQuestion.created_at.desc())
            )
        ).all()
    )
    return [
        BookmarkOut(
            question_id=b.question_id,
            folder_name=b.folder_name,
            created_at=b.created_at,
        )
        for b in rows
    ]


@bookmarks_router.post("", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
async def save_bookmark(
    payload: BookmarkCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("notes:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> BookmarkOut:
    existing = await db.get(SavedQuestion, (caller.id, payload.question_id))
    if existing is not None:
        existing.folder_name = payload.folder_name
        await db.commit()
        await db.refresh(existing)
        return BookmarkOut(
            question_id=existing.question_id,
            folder_name=existing.folder_name,
            created_at=existing.created_at,
        )
    bm = SavedQuestion(
        student_id=caller.id,
        question_id=payload.question_id,
        folder_name=payload.folder_name,
    )
    db.add(bm)
    await db.commit()
    await db.refresh(bm)
    return BookmarkOut(
        question_id=bm.question_id,
        folder_name=bm.folder_name,
        created_at=bm.created_at,
    )


@bookmarks_router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(
    question_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("notes:manage_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> None:
    existing = await db.get(SavedQuestion, (caller.id, question_id))
    if existing is None:
        raise AppError(status_code=404, code="BOOKMARK_NOT_FOUND", message="Bookmark not found.")
    await db.delete(existing)
    await db.commit()
