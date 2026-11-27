"""Pydantic v2 schemas for Teacher Ecosystem (F-031)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TeacherClassCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    grade_label: str = Field(min_length=1, max_length=40)
    subject_name: str = Field(min_length=2, max_length=80)
    school_id: UUID | None = None
    branch_id: UUID | None = None
    academic_year_id: UUID | None = None


class TeacherSectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=32)
    capacity: int = Field(default=40, ge=1, le=500)


class TeacherSectionResponse(BaseModel):
    id: UUID
    class_id: UUID
    name: str
    code: str
    capacity: int
    enrolled_count: int = 0


class TeacherClassResponse(BaseModel):
    id: UUID
    tenant_id: UUID | None
    teacher_id: UUID
    name: str
    grade_label: str
    subject_name: str
    status: str
    sections_count: int = 0
    students_count: int = 0
    assignments_count: int = 0
    created_at: datetime


class ClassEnrollStudentRequest(BaseModel):
    student_email: EmailStr
    section_id: UUID | None = None
    roll_no: str | None = Field(default=None, max_length=32)


class ClassEnrollmentResponse(BaseModel):
    id: UUID
    class_id: UUID
    section_id: UUID | None
    section_name: str | None
    student_id: UUID
    student_name: str
    student_email: str
    roll_no: str | None
    status: str
    enrolled_at: datetime


class QuestionBankOptionItem(BaseModel):
    question_id: UUID
    question_version_id: UUID
    question_type: str
    difficulty: str
    default_marks: float
    stem_preview: str


class TeacherAssignmentCreateRequest(BaseModel):
    class_id: UUID
    section_id: UUID | None = None
    title: str = Field(min_length=3, max_length=200)
    instructions: str = Field(default="", max_length=4000)
    assignment_type: Literal["assignment", "quiz", "test"] = "assignment"
    question_ids: list[UUID] = Field(default_factory=list, max_length=100)
    max_marks: float = Field(default=20.0, gt=0, le=500)
    due_at: datetime | None = None
    status: Literal["draft", "published", "closed"] = "published"


class TeacherAssignmentResponse(BaseModel):
    id: UUID
    class_id: UUID
    section_id: UUID | None
    teacher_id: UUID
    title: str
    instructions: str
    assignment_type: str
    question_ids: list[str]
    max_marks: float
    due_at: datetime | None
    status: str
    submissions_count: int = 0
    graded_count: int = 0
    created_at: datetime


class StudentAssignmentSubmitRequest(BaseModel):
    response_text: str = Field(min_length=1, max_length=10000)
    homework_submission_id: UUID | None = None


class TeacherOverrideGradeRequest(BaseModel):
    teacher_score: float = Field(ge=0.0, le=500.0)
    teacher_feedback: str = Field(default="", max_length=4000)
    teacher_override_reason: str | None = Field(default=None, max_length=1000)
    status: Literal["teacher_reviewed", "returned"] = "returned"


class AssignmentSubmissionResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    student_id: UUID
    student_name: str
    student_email: str
    response_text: str
    ai_suggested_score: float | None
    ai_feedback_summary: str | None
    teacher_score: float | None
    teacher_override_reason: str | None
    teacher_feedback: str | None
    effective_score: float | None
    max_marks: float
    status: str
    graded_by: UUID | None
    graded_at: datetime | None
    created_at: datetime


class WeakConceptItem(BaseModel):
    concept_id: UUID
    average_mastery_pct: float
    affected_students_count: int


class TeacherClassAnalyticsResponse(BaseModel):
    class_id: UUID
    class_name: str
    total_students: int
    total_assignments: int
    total_submissions: int
    graded_submissions: int
    average_score_pct: float
    average_mastery_pct: float
    weak_concepts: list[WeakConceptItem]


class TeacherStudentAnalyticsResponse(BaseModel):
    student_id: UUID
    student_name: str
    student_email: str
    enrolled_classes_count: int
    practice_total_attempts: int
    practice_accuracy_pct: float
    mastery_average_pct: float
    weak_concepts: list[WeakConceptItem]
    submissions_total: int
    submissions_average_pct: float


class TeacherDashboardResponse(BaseModel):
    teacher_id: UUID
    total_classes: int
    total_students: int
    total_assignments: int
    pending_reviews_count: int
    classes: list[TeacherClassResponse]
    recent_assignments: list[TeacherAssignmentResponse]
