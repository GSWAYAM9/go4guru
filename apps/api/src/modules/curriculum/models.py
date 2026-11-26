"""ORM models for the 11-level versioned curriculum hierarchy."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

JSONBVariant = JSON().with_variant(JSONB(), "postgresql")


class Board(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "boards"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    country: Mapped[str] = mapped_column(String(64), server_default=text("'IN'"), nullable=False)


class AcademicSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academic_sessions"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)


class Grade(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grades"

    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)


class CurriculumVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "curriculum_versions"
    __table_args__ = (
        UniqueConstraint(
            "board_id",
            "academic_session_id",
            "version_tag",
            name="uq_curriculum_versions_board_session_tag",
        ),
    )

    board_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("boards.id", ondelete="RESTRICT"), nullable=False
    )
    academic_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), server_default=text("'draft'"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Subject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subjects"

    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    discipline: Mapped[str] = mapped_column(String(48), nullable=False)


class Book(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "books"

    curriculum_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("curriculum_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    grade_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("grades.id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    publisher: Mapped[str] = mapped_column(String(120), nullable=False)
    official_source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    edition_year: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Chapter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("book_id", "code", name="uq_chapters_book_code"),)

    book_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class Section(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sections"

    chapter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)


class Topic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "topics"

    chapter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)


class Concept(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint("curriculum_version_id", "code", name="uq_concepts_version_code"),
    )

    topic_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    curriculum_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("curriculum_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    difficulty_baseline: Mapped[int] = mapped_column(
        Integer, server_default=text("2"), nullable=False
    )
    skill_tags_jsonb: Mapped[list[str]] = mapped_column(JSONBVariant, nullable=False, default=list)
    exam_tags_jsonb: Mapped[list[str]] = mapped_column(JSONBVariant, nullable=False, default=list)


class LearningObjective(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_objectives"

    concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    bloom_level: Mapped[str] = mapped_column(String(32), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)


class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"

    concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    strength: Mapped[str] = mapped_column(
        String(24), server_default=text("'required'"), nullable=False
    )


class ExamTrack(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exam_tracks"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class ExamConceptMapping(Base):
    __tablename__ = "exam_concept_mappings"

    exam_track_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("exam_tracks.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    weightage_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    priority_tier: Mapped[str] = mapped_column(
        String(16), server_default=text("'core'"), nullable=False
    )
