"""Pydantic schemas for the 11-level versioned curriculum hierarchy."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

BloomLevel = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]


class BoardCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=160)
    country: str = Field(default="IN", max_length=64)


class BoardOut(BaseModel):
    id: UUID
    code: str
    name: str
    country: str


class AcademicSessionCreate(BaseModel):
    code: str = Field(min_length=3, max_length=32)
    starts_on: date
    ends_on: date
    is_active: bool = True


class AcademicSessionOut(BaseModel):
    id: UUID
    code: str
    starts_on: date
    ends_on: date
    is_active: bool


class GradeOut(BaseModel):
    id: UUID
    number: int
    label: str


class ExamTrackOut(BaseModel):
    id: UUID
    code: str
    name: str


class CurriculumVersionCreate(BaseModel):
    board_id: UUID
    academic_session_id: UUID
    version_tag: str = Field(min_length=2, max_length=64)


class CurriculumVersionOut(BaseModel):
    id: UUID
    board_id: UUID
    academic_session_id: UUID
    version_tag: str
    status: str
    published_at: datetime | None


class SubjectCreate(BaseModel):
    code: str = Field(min_length=2, max_length=48)
    name: str = Field(min_length=2, max_length=120)
    discipline: str = Field(min_length=2, max_length=48)


class SubjectOut(BaseModel):
    id: UUID
    code: str
    name: str
    discipline: str


class BookCreate(BaseModel):
    curriculum_version_id: UUID
    grade_id: UUID
    subject_id: UUID
    title: str = Field(min_length=2, max_length=200)
    publisher: str = Field(min_length=2, max_length=120)
    official_source_url: str | None = Field(default=None, max_length=512)
    edition_year: int | None = Field(default=None, ge=1990, le=2035)


class ChapterCreate(BaseModel):
    book_id: UUID
    sequence_no: int = Field(ge=1)
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=2, max_length=220)
    summary: str | None = None


class SectionCreate(BaseModel):
    chapter_id: UUID
    sequence_no: int = Field(ge=1)
    title: str = Field(min_length=2, max_length=220)


class TopicCreate(BaseModel):
    chapter_id: UUID
    section_id: UUID | None = None
    sequence_no: int = Field(ge=1)
    title: str = Field(min_length=2, max_length=220)


class ConceptCreate(BaseModel):
    topic_id: UUID
    code: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=220)
    difficulty_baseline: int = Field(default=2, ge=1, le=5)
    skill_tags: list[str] = Field(default_factory=list)
    exam_tags: list[str] = Field(default_factory=list)


class LearningObjectiveCreate(BaseModel):
    concept_id: UUID
    bloom_level: BloomLevel
    statement: str = Field(min_length=4)


class PrerequisiteCreate(BaseModel):
    concept_id: UUID
    prerequisite_concept_id: UUID
    strength: Literal["required", "recommended"] = "required"


class LearningObjectiveNode(BaseModel):
    id: UUID
    bloom_level: str
    statement: str


class PrerequisiteNode(BaseModel):
    prerequisite_concept_id: UUID
    strength: str


class ConceptNode(BaseModel):
    id: UUID
    code: str
    title: str
    difficulty_baseline: int
    skill_tags: list[str]
    exam_tags: list[str]
    learning_objectives: list[LearningObjectiveNode]
    prerequisites: list[PrerequisiteNode]


class TopicNode(BaseModel):
    id: UUID
    section_id: UUID | None
    sequence_no: int
    title: str
    concepts: list[ConceptNode]


class SectionNode(BaseModel):
    id: UUID
    sequence_no: int
    title: str


class ChapterNode(BaseModel):
    id: UUID
    sequence_no: int
    code: str
    title: str
    summary: str | None
    sections: list[SectionNode]
    topics: list[TopicNode]


class BookNode(BaseModel):
    id: UUID
    grade_id: UUID
    grade_label: str
    subject_id: UUID
    subject_name: str
    title: str
    publisher: str
    official_source_url: str | None
    edition_year: int | None
    chapters: list[ChapterNode]


class CurriculumTreeResponse(BaseModel):
    version: CurriculumVersionOut
    board: BoardOut
    academic_session: AcademicSessionOut
    books: list[BookNode]
