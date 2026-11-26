"""Public contract boundary for curriculum module."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.curriculum.models import (
    Board,
    Book,
    Chapter,
    Concept,
    ConceptPrerequisite,
    CurriculumVersion,
    ExamTrack,
    Grade,
    LearningObjective,
    Subject,
    Topic,
)
from src.modules.curriculum.router import curriculum_router

MODULE_NAME = "curriculum"
MODULE_PHASE = "Phase 1"
MODULE_STATUS = "IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class ResolvedCurriculumContext:
    """Resolved UUIDs for mapping questions/imports onto curriculum hierarchy."""

    curriculum_version_id: UUID
    grade_id: UUID
    subject_id: UUID
    chapter_id: UUID
    topic_id: UUID | None
    concept_id: UUID | None


async def resolve_hierarchy_by_names(
    db: AsyncSession,
    *,
    grade_number: int | None,
    subject_name_or_code: str | None,
    chapter_title_or_code: str | None,
    topic_title: str | None = None,
    concept_code: str | None = None,
) -> ResolvedCurriculumContext | None:
    """Resolve published/active academic node IDs by labels during Excel import mapping."""
    if chapter_title_or_code is None:
        return None
    stmt = (
        select(Chapter, Book, Grade, Subject)
        .join(Book, Chapter.book_id == Book.id)
        .join(Grade, Book.grade_id == Grade.id)
        .join(Subject, Book.subject_id == Subject.id)
    )
    if grade_number is not None:
        stmt = stmt.where(Grade.number == grade_number)
    if subject_name_or_code:
        norm_subj = subject_name_or_code.strip().lower()
        stmt = stmt.where((Subject.name.ilike(norm_subj)) | (Subject.code.ilike(norm_subj)))
    norm_chap = chapter_title_or_code.strip()
    stmt = stmt.where((Chapter.title.ilike(norm_chap)) | (Chapter.code.ilike(norm_chap)))
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    chapter, book, grade, subject = row

    topic_id: UUID | None = None
    if topic_title:
        topic_id = await db.scalar(
            select(Topic.id).where(
                Topic.chapter_id == chapter.id, Topic.title.ilike(topic_title.strip())
            )
        )

    concept_id: UUID | None = None
    if concept_code:
        concept_id = await db.scalar(
            select(Concept.id).where(
                Concept.curriculum_version_id == book.curriculum_version_id,
                Concept.code.ilike(concept_code.strip()),
            )
        )

    return ResolvedCurriculumContext(
        curriculum_version_id=book.curriculum_version_id,
        grade_id=grade.id,
        subject_id=subject.id,
        chapter_id=chapter.id,
        topic_id=topic_id,
        concept_id=concept_id,
    )


async def get_chapter_and_subject_labels(
    db: AsyncSession,
) -> tuple[dict[UUID, str], dict[UUID, str]]:
    """Return ID->title maps for chapters and subjects (read-only contract)."""
    chapters = {c.id: c.title for c in (await db.scalars(select(Chapter))).all()}
    subjects = {s.id: s.name for s in (await db.scalars(select(Subject))).all()}
    return chapters, subjects


async def get_exam_tracks_map(db: AsyncSession) -> dict[UUID, tuple[str, str]]:
    """Return map of exam_track_id -> (code, name)."""
    tracks = (await db.scalars(select(ExamTrack))).all()
    return {t.id: (t.code, t.name) for t in tracks}


@dataclass(frozen=True, slots=True)
class ResolvedTutorCurriculumContract:
    """Resolved academic metadata, objectives, and prerequisites for AI grounding."""

    curriculum_version_id: UUID | None
    board_code: str | None
    grade_id: UUID | None
    grade_number: int | None
    subject_id: UUID | None
    subject_name: str | None
    discipline: str | None
    chapter_id: UUID | None
    chapter_title: str | None
    topic_id: UUID | None
    topic_title: str | None
    concept_id: UUID | None
    concept_title: str | None
    learning_objectives: tuple[str, ...]
    prerequisites: tuple[str, ...]


async def resolve_tutor_curriculum_context(
    db: AsyncSession,
    *,
    board_id: UUID | None = None,
    curriculum_version_id: UUID | None = None,
    grade_id: UUID | None = None,
    subject_id: UUID | None = None,
    chapter_id: UUID | None = None,
    topic_id: UUID | None = None,
    concept_id: UUID | None = None,
) -> ResolvedTutorCurriculumContract:
    """Resolve readable hierarchy context, learning objectives, and prerequisite titles."""
    board_code: str | None = None
    if board_id:
        b = await db.get(Board, board_id)
        board_code = b.code if b else None

    cv_id = curriculum_version_id
    if cv_id and not board_code:
        cv = await db.get(CurriculumVersion, cv_id)
        if cv:
            b = await db.get(Board, cv.board_id)
            board_code = b.code if b else None

    grade_num: int | None = None
    if grade_id:
        g = await db.get(Grade, grade_id)
        grade_num = g.number if g else None

    subject_name: str | None = None
    discipline: str | None = None
    if subject_id:
        s = await db.get(Subject, subject_id)
        if s:
            subject_name = s.name
            discipline = s.discipline

    chapter_title: str | None = None
    if chapter_id:
        c = await db.get(Chapter, chapter_id)
        if c:
            chapter_title = c.title
            book = await db.get(Book, c.book_id)
            if book:
                cv_id = cv_id or book.curriculum_version_id
                if not grade_id:
                    grade_id = book.grade_id
                    g = await db.get(Grade, grade_id)
                    grade_num = g.number if g else None
                if not subject_id:
                    subject_id = book.subject_id
                    s = await db.get(Subject, subject_id)
                    if s:
                        subject_name = s.name
                        discipline = s.discipline

    topic_title: str | None = None
    if topic_id:
        t = await db.get(Topic, topic_id)
        topic_title = t.title if t else None

    concept_title: str | None = None
    objectives: list[str] = []
    prereq_titles: list[str] = []
    if concept_id:
        con = await db.get(Concept, concept_id)
        if con:
            concept_title = con.title
            obj_rows = (
                await db.scalars(
                    select(LearningObjective.statement).where(
                        LearningObjective.concept_id == con.id
                    )
                )
            ).all()
            objectives = [str(o) for o in obj_rows]
            prereq_ids = (
                await db.scalars(
                    select(ConceptPrerequisite.prerequisite_concept_id).where(
                        ConceptPrerequisite.concept_id == con.id
                    )
                )
            ).all()
            if prereq_ids:
                p_rows = (
                    await db.scalars(select(Concept.title).where(Concept.id.in_(prereq_ids)))
                ).all()
                prereq_titles = [str(p) for p in p_rows]

    return ResolvedTutorCurriculumContract(
        curriculum_version_id=cv_id,
        board_code=board_code,
        grade_id=grade_id,
        grade_number=grade_num,
        subject_id=subject_id,
        subject_name=subject_name,
        discipline=discipline,
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        topic_id=topic_id,
        topic_title=topic_title,
        concept_id=concept_id,
        concept_title=concept_title,
        learning_objectives=tuple(objectives),
        prerequisites=tuple(prereq_titles),
    )


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "ConceptGraphSnapshot",
    "ConceptNodeContract",
    "ResolvedCurriculumContext",
    "ResolvedTutorCurriculumContract",
    "curriculum_router",
    "get_chapter_and_subject_labels",
    "get_concept_graph_snapshot",
    "get_exam_tracks_map",
    "resolve_hierarchy_by_names",
    "resolve_tutor_curriculum_context",
]


@dataclass(frozen=True, slots=True)
class ConceptNodeContract:
    """Curriculum concept node + parent chapter/subject labels for adaptive graphs."""

    concept_id: UUID
    code: str
    title: str
    chapter_id: UUID | None
    chapter_title: str | None
    subject_id: UUID | None
    subject_name: str | None


@dataclass(frozen=True, slots=True)
class ConceptGraphSnapshot:
    """Concept catalog plus prerequisite/dependent adjacency maps."""

    concepts: dict[UUID, ConceptNodeContract]
    prerequisites_of: dict[UUID, tuple[UUID, ...]]
    dependents_of: dict[UUID, tuple[UUID, ...]]


async def get_concept_graph_snapshot(db: AsyncSession) -> ConceptGraphSnapshot:
    """Return active concepts and prerequisite/downstream edges across curriculum versions."""
    chap_rows = (
        await db.execute(
            select(Chapter.id, Chapter.title, Book.subject_id, Subject.name)
            .join(Book, Chapter.book_id == Book.id)
            .join(Subject, Book.subject_id == Subject.id)
        )
    ).all()
    chap_meta: dict[UUID, tuple[str, UUID, str]] = {
        cid: (ctitle, sid, sname) for cid, ctitle, sid, sname in chap_rows
    }

    topic_rows = (await db.execute(select(Topic.id, Topic.chapter_id))).all()
    topic_to_chap: dict[UUID, UUID] = {tid: chid for tid, chid in topic_rows}

    concepts_rows = (await db.scalars(select(Concept).order_by(Concept.title.asc()))).all()
    concepts: dict[UUID, ConceptNodeContract] = {}
    for c in concepts_rows:
        ch_id = topic_to_chap.get(c.topic_id)
        meta = chap_meta.get(ch_id) if ch_id else None
        concepts[c.id] = ConceptNodeContract(
            concept_id=c.id,
            code=c.code,
            title=c.title,
            chapter_id=ch_id,
            chapter_title=meta[0] if meta else None,
            subject_id=meta[1] if meta else None,
            subject_name=meta[2] if meta else None,
        )

    edges = (await db.scalars(select(ConceptPrerequisite))).all()
    prereq_lists: dict[UUID, list[UUID]] = {}
    dep_lists: dict[UUID, list[UUID]] = {}
    for edge in edges:
        prereq_lists.setdefault(edge.concept_id, []).append(edge.prerequisite_concept_id)
        dep_lists.setdefault(edge.prerequisite_concept_id, []).append(edge.concept_id)

    return ConceptGraphSnapshot(
        concepts=concepts,
        prerequisites_of={k: tuple(v) for k, v in prereq_lists.items()},
        dependents_of={k: tuple(v) for k, v in dep_lists.items()},
    )
