"""Repository queries and service logic for 11-level versioned curriculum."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.errors import AppError
from src.modules.curriculum.models import (
    AcademicSession,
    Board,
    Book,
    Chapter,
    Concept,
    ConceptPrerequisite,
    CurriculumVersion,
    ExamTrack,
    Grade,
    LearningObjective,
    Section,
    Subject,
    Topic,
)
from src.modules.curriculum.schemas import (
    AcademicSessionCreate,
    AcademicSessionOut,
    BoardCreate,
    BoardOut,
    BookCreate,
    BookNode,
    ChapterCreate,
    ChapterNode,
    ConceptCreate,
    ConceptNode,
    CurriculumTreeResponse,
    CurriculumVersionCreate,
    CurriculumVersionOut,
    LearningObjectiveCreate,
    LearningObjectiveNode,
    PrerequisiteCreate,
    PrerequisiteNode,
    SectionCreate,
    SectionNode,
    SubjectCreate,
    TopicCreate,
    TopicNode,
)


class CurriculumService:
    """Manages versioned curriculum hierarchy, DAG validation, and publishing."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_boards(self) -> list[Board]:
        return list((await self.db.scalars(select(Board).order_by(Board.code))).all())

    async def create_board(self, payload: BoardCreate, caller: AuthenticatedUser) -> Board:
        existing = await self.db.scalar(select(Board).where(Board.code == payload.code.upper()))
        if existing is not None:
            raise AppError(status_code=409, code="BOARD_EXISTS", message="Board code exists.")
        board = Board(code=payload.code.upper(), name=payload.name, country=payload.country)
        self.db.add(board)
        await self.db.flush()
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="curriculum.board_created",
            resource_type="board",
            resource_id=str(board.id),
        )
        await self.db.commit()
        await self.db.refresh(board)
        return board

    async def list_sessions(self) -> list[AcademicSession]:
        return list(
            (
                await self.db.scalars(select(AcademicSession).order_by(AcademicSession.code.desc()))
            ).all()
        )

    async def create_session(
        self, payload: AcademicSessionCreate, caller: AuthenticatedUser
    ) -> AcademicSession:
        if payload.ends_on <= payload.starts_on:
            raise AppError(
                status_code=422,
                code="INVALID_SESSION_DATES",
                message="Session ends_on must be after starts_on.",
            )
        existing = await self.db.scalar(
            select(AcademicSession).where(AcademicSession.code == payload.code)
        )
        if existing is not None:
            raise AppError(status_code=409, code="SESSION_EXISTS", message="Session exists.")
        sess = AcademicSession(
            code=payload.code,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            is_active=payload.is_active,
        )
        self.db.add(sess)
        await self.db.flush()
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="curriculum.session_created",
            resource_type="academic_session",
            resource_id=str(sess.id),
        )
        await self.db.commit()
        await self.db.refresh(sess)
        return sess

    async def list_grades(self) -> list[Grade]:
        return list((await self.db.scalars(select(Grade).order_by(Grade.number))).all())

    async def list_subjects(self) -> list[Subject]:
        return list((await self.db.scalars(select(Subject).order_by(Subject.name))).all())

    async def create_subject(self, payload: SubjectCreate, caller: AuthenticatedUser) -> Subject:
        existing = await self.db.scalar(select(Subject).where(Subject.code == payload.code.upper()))
        if existing is not None:
            raise AppError(status_code=409, code="SUBJECT_EXISTS", message="Subject code exists.")
        subj = Subject(
            code=payload.code.upper(), name=payload.name, discipline=payload.discipline.lower()
        )
        self.db.add(subj)
        await self.db.flush()
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="curriculum.subject_created",
            resource_type="subject",
            resource_id=str(subj.id),
        )
        await self.db.commit()
        await self.db.refresh(subj)
        return subj

    async def list_exam_tracks(self) -> list[ExamTrack]:
        return list((await self.db.scalars(select(ExamTrack).order_by(ExamTrack.code))).all())

    async def list_versions(self, *, include_drafts: bool) -> list[CurriculumVersion]:
        stmt = select(CurriculumVersion)
        if not include_drafts:
            stmt = stmt.where(CurriculumVersion.status == "published")
        stmt = stmt.order_by(CurriculumVersion.created_at.desc())
        return list((await self.db.scalars(stmt)).all())

    async def create_version(
        self, payload: CurriculumVersionCreate, caller: AuthenticatedUser
    ) -> CurriculumVersion:
        board = await self.db.get(Board, payload.board_id)
        sess = await self.db.get(AcademicSession, payload.academic_session_id)
        if board is None or sess is None:
            raise AppError(
                status_code=404,
                code="REFERENCE_NOT_FOUND",
                message="Board or academic session not found.",
            )
        ver = CurriculumVersion(
            board_id=payload.board_id,
            academic_session_id=payload.academic_session_id,
            version_tag=payload.version_tag,
            status="draft",
        )
        self.db.add(ver)
        await self.db.flush()
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="curriculum.version_created",
            resource_type="curriculum_version",
            resource_id=str(ver.id),
        )
        await self.db.commit()
        await self.db.refresh(ver)
        return ver

    async def publish_version(
        self, version_id: UUID, caller: AuthenticatedUser
    ) -> CurriculumVersion:
        ver = await self.db.get(CurriculumVersion, version_id)
        if ver is None:
            raise AppError(status_code=404, code="VERSION_NOT_FOUND", message="Version not found.")
        ver.status = "published"
        ver.published_at = datetime.now(UTC)
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0],
            action="curriculum.version_published",
            resource_type="curriculum_version",
            resource_id=str(ver.id),
        )
        await self.db.commit()
        await self.db.refresh(ver)
        return ver

    async def create_book(self, payload: BookCreate, caller: AuthenticatedUser) -> Book:
        ver = await self.db.get(CurriculumVersion, payload.curriculum_version_id)
        grade = await self.db.get(Grade, payload.grade_id)
        subj = await self.db.get(Subject, payload.subject_id)
        if ver is None or grade is None or subj is None:
            raise AppError(
                status_code=404,
                code="REFERENCE_NOT_FOUND",
                message="Curriculum version, grade, or subject not found.",
            )
        book = Book(**payload.model_dump())
        self.db.add(book)
        await self.db.commit()
        await self.db.refresh(book)
        return book

    async def create_chapter(self, payload: ChapterCreate, caller: AuthenticatedUser) -> Chapter:
        if await self.db.get(Book, payload.book_id) is None:
            raise AppError(status_code=404, code="BOOK_NOT_FOUND", message="Book not found.")
        ch = Chapter(**payload.model_dump())
        self.db.add(ch)
        await self.db.commit()
        await self.db.refresh(ch)
        return ch

    async def create_section(self, payload: SectionCreate) -> Section:
        if await self.db.get(Chapter, payload.chapter_id) is None:
            raise AppError(status_code=404, code="CHAPTER_NOT_FOUND", message="Chapter not found.")
        sec = Section(**payload.model_dump())
        self.db.add(sec)
        await self.db.commit()
        await self.db.refresh(sec)
        return sec

    async def create_topic(self, payload: TopicCreate) -> Topic:
        if await self.db.get(Chapter, payload.chapter_id) is None:
            raise AppError(status_code=404, code="CHAPTER_NOT_FOUND", message="Chapter not found.")
        topic = Topic(**payload.model_dump())
        self.db.add(topic)
        await self.db.commit()
        await self.db.refresh(topic)
        return topic

    async def create_concept(self, payload: ConceptCreate) -> Concept:
        topic = await self.db.get(Topic, payload.topic_id)
        if topic is None:
            raise AppError(status_code=404, code="TOPIC_NOT_FOUND", message="Topic not found.")
        chapter = await self.db.get(Chapter, topic.chapter_id)
        assert chapter is not None
        book = await self.db.get(Book, chapter.book_id)
        assert book is not None
        concept = Concept(
            topic_id=payload.topic_id,
            curriculum_version_id=book.curriculum_version_id,
            code=payload.code,
            title=payload.title,
            difficulty_baseline=payload.difficulty_baseline,
            skill_tags_jsonb=payload.skill_tags,
            exam_tags_jsonb=payload.exam_tags,
        )
        self.db.add(concept)
        await self.db.commit()
        await self.db.refresh(concept)
        return concept

    async def create_learning_objective(
        self, payload: LearningObjectiveCreate
    ) -> LearningObjective:
        if await self.db.get(Concept, payload.concept_id) is None:
            raise AppError(status_code=404, code="CONCEPT_NOT_FOUND", message="Concept not found.")
        lo = LearningObjective(**payload.model_dump())
        self.db.add(lo)
        await self.db.commit()
        await self.db.refresh(lo)
        return lo

    async def add_prerequisite(self, payload: PrerequisiteCreate) -> PrerequisiteNode:
        """Insert a directed prerequisite edge after enforcing DAG acyclicity."""
        if payload.concept_id == payload.prerequisite_concept_id:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="CYCLIC_PREREQUISITE",
                message="A concept cannot depend on itself.",
            )
        c1 = await self.db.get(Concept, payload.concept_id)
        c2 = await self.db.get(Concept, payload.prerequisite_concept_id)
        if c1 is None or c2 is None:
            raise AppError(
                status_code=404,
                code="CONCEPT_NOT_FOUND",
                message="Concept or prerequisite missing.",
            )

        # Check if concept_id is reachable as a prerequisite ancestor of prerequisite_concept_id.
        edges = list((await self.db.scalars(select(ConceptPrerequisite))).all())
        prereq_map: dict[UUID, list[UUID]] = {}
        for edge in edges:
            prereq_map.setdefault(edge.concept_id, []).append(edge.prerequisite_concept_id)

        queue: deque[UUID] = deque([payload.prerequisite_concept_id])
        visited: set[UUID] = set()
        while queue:
            cur = queue.popleft()
            if cur == payload.concept_id:
                raise AppError(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    code="CYCLIC_PREREQUISITE",
                    message="Adding this prerequisite creates a circular dependency cycle.",
                )
            if cur in visited:
                continue
            visited.add(cur)
            queue.extend(prereq_map.get(cur, []))

        existing = await self.db.scalar(
            select(ConceptPrerequisite).where(
                ConceptPrerequisite.concept_id == payload.concept_id,
                ConceptPrerequisite.prerequisite_concept_id == payload.prerequisite_concept_id,
            )
        )
        if existing is None:
            edge_obj = ConceptPrerequisite(
                concept_id=payload.concept_id,
                prerequisite_concept_id=payload.prerequisite_concept_id,
                strength=payload.strength,
            )
            self.db.add(edge_obj)
            await self.db.commit()
        return PrerequisiteNode(
            prerequisite_concept_id=payload.prerequisite_concept_id,
            strength=payload.strength,
        )

    async def get_tree(
        self,
        *,
        version_id: UUID | None = None,
        grade_id: UUID | None = None,
        subject_id: UUID | None = None,
        include_drafts: bool = False,
    ) -> CurriculumTreeResponse | None:
        if version_id is not None:
            ver = await self.db.get(CurriculumVersion, version_id)
        else:
            stmt = select(CurriculumVersion)
            if not include_drafts:
                stmt = stmt.where(CurriculumVersion.status == "published")
            stmt = stmt.order_by(
                CurriculumVersion.published_at.desc(), CurriculumVersion.created_at.desc()
            )
            ver = await self.db.scalar(stmt)

        if ver is None:
            return None
        if not include_drafts and ver.status != "published":
            raise AppError(
                status_code=403,
                code="CURRICULUM_NOT_PUBLISHED",
                message="Unpublished curriculum versions require admin permissions.",
            )

        board = await self.db.get(Board, ver.board_id)
        sess = await self.db.get(AcademicSession, ver.academic_session_id)
        assert board is not None and sess is not None

        book_stmt = select(Book).where(Book.curriculum_version_id == ver.id)
        if grade_id is not None:
            book_stmt = book_stmt.where(Book.grade_id == grade_id)
        if subject_id is not None:
            book_stmt = book_stmt.where(Book.subject_id == subject_id)
        books = list((await self.db.scalars(book_stmt.order_by(Book.title))).all())

        grades_by_id = {g.id: g for g in await self.list_grades()}
        subjects_by_id = {s.id: s for s in await self.list_subjects()}

        book_ids = [b.id for b in books]
        chapters = (
            list(
                (
                    await self.db.scalars(
                        select(Chapter)
                        .where(Chapter.book_id.in_(book_ids))
                        .order_by(Chapter.sequence_no)
                    )
                ).all()
            )
            if book_ids
            else []
        )
        chapter_ids = [c.id for c in chapters]
        sections = (
            list(
                (
                    await self.db.scalars(
                        select(Section)
                        .where(Section.chapter_id.in_(chapter_ids))
                        .order_by(Section.sequence_no)
                    )
                ).all()
            )
            if chapter_ids
            else []
        )
        topics = (
            list(
                (
                    await self.db.scalars(
                        select(Topic)
                        .where(Topic.chapter_id.in_(chapter_ids))
                        .order_by(Topic.sequence_no)
                    )
                ).all()
            )
            if chapter_ids
            else []
        )
        topic_ids = [t.id for t in topics]
        concepts = (
            list(
                (
                    await self.db.scalars(
                        select(Concept)
                        .where(Concept.topic_id.in_(topic_ids))
                        .order_by(Concept.code)
                    )
                ).all()
            )
            if topic_ids
            else []
        )
        concept_ids = [c.id for c in concepts]
        los = (
            list(
                (
                    await self.db.scalars(
                        select(LearningObjective).where(
                            LearningObjective.concept_id.in_(concept_ids)
                        )
                    )
                ).all()
            )
            if concept_ids
            else []
        )
        prereqs = (
            list(
                (
                    await self.db.scalars(
                        select(ConceptPrerequisite).where(
                            ConceptPrerequisite.concept_id.in_(concept_ids)
                        )
                    )
                ).all()
            )
            if concept_ids
            else []
        )

        lo_map: dict[UUID, list[LearningObjectiveNode]] = {}
        for lo in los:
            lo_map.setdefault(lo.concept_id, []).append(
                LearningObjectiveNode(id=lo.id, bloom_level=lo.bloom_level, statement=lo.statement)
            )
        pr_map: dict[UUID, list[PrerequisiteNode]] = {}
        for pr in prereqs:
            pr_map.setdefault(pr.concept_id, []).append(
                PrerequisiteNode(
                    prerequisite_concept_id=pr.prerequisite_concept_id,
                    strength=pr.strength,
                )
            )
        concept_map: dict[UUID, list[ConceptNode]] = {}
        for cp in concepts:
            concept_map.setdefault(cp.topic_id, []).append(
                ConceptNode(
                    id=cp.id,
                    code=cp.code,
                    title=cp.title,
                    difficulty_baseline=cp.difficulty_baseline,
                    skill_tags=list(cp.skill_tags_jsonb),
                    exam_tags=list(cp.exam_tags_jsonb),
                    learning_objectives=lo_map.get(cp.id, []),
                    prerequisites=pr_map.get(cp.id, []),
                )
            )
        topic_map: dict[UUID, list[TopicNode]] = {}
        for tp in topics:
            topic_map.setdefault(tp.chapter_id, []).append(
                TopicNode(
                    id=tp.id,
                    section_id=tp.section_id,
                    sequence_no=tp.sequence_no,
                    title=tp.title,
                    concepts=concept_map.get(tp.id, []),
                )
            )
        sec_map: dict[UUID, list[SectionNode]] = {}
        for sc in sections:
            sec_map.setdefault(sc.chapter_id, []).append(
                SectionNode(id=sc.id, sequence_no=sc.sequence_no, title=sc.title)
            )
        ch_map: dict[UUID, list[ChapterNode]] = {}
        for ch in chapters:
            ch_map.setdefault(ch.book_id, []).append(
                ChapterNode(
                    id=ch.id,
                    sequence_no=ch.sequence_no,
                    code=ch.code,
                    title=ch.title,
                    summary=ch.summary,
                    sections=sec_map.get(ch.id, []),
                    topics=topic_map.get(ch.id, []),
                )
            )

        book_nodes: list[BookNode] = []
        for bk in books:
            grade = grades_by_id.get(bk.grade_id)
            subj = subjects_by_id.get(bk.subject_id)
            book_nodes.append(
                BookNode(
                    id=bk.id,
                    grade_id=bk.grade_id,
                    grade_label=grade.label if grade else "Unknown",
                    subject_id=bk.subject_id,
                    subject_name=subj.name if subj else "Unknown",
                    title=bk.title,
                    publisher=bk.publisher,
                    official_source_url=bk.official_source_url,
                    edition_year=bk.edition_year,
                    chapters=ch_map.get(bk.id, []),
                )
            )

        return CurriculumTreeResponse(
            version=CurriculumVersionOut(
                id=ver.id,
                board_id=ver.board_id,
                academic_session_id=ver.academic_session_id,
                version_tag=ver.version_tag,
                status=ver.status,
                published_at=ver.published_at,
            ),
            board=BoardOut(id=board.id, code=board.code, name=board.name, country=board.country),
            academic_session=AcademicSessionOut(
                id=sess.id,
                code=sess.code,
                starts_on=sess.starts_on,
                ends_on=sess.ends_on,
                is_active=sess.is_active,
            ),
            books=book_nodes,
        )
