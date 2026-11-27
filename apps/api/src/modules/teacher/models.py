"""ORM models for Teacher Ecosystem (F-031)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.core.outbox import JSONBVariant


class TeacherClass(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teacher_classes"
    __table_args__ = (
        Index("ix_teacher_classes_teacher", "teacher_id", "status"),
        Index("ix_teacher_classes_tenant", "tenant_id", "status"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    school_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    branch_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    academic_year_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    grade_label: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )


class TeacherSection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teacher_sections"
    __table_args__ = (UniqueConstraint("class_id", "code", name="uq_teacher_sections_class_code"),)

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    class_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teacher_classes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, server_default=text("40"), nullable=False)


class ClassEnrollment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "class_enrollments"
    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_class_enrollments_class_student"),
        Index("ix_class_enrollments_student", "student_id", "status"),
        Index("ix_class_enrollments_tenant", "tenant_id", "class_id"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    class_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teacher_classes.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teacher_sections.id", ondelete="SET NULL"), nullable=True
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    roll_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TeacherAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teacher_assignments"
    __table_args__ = (
        Index("ix_teacher_assignments_class", "class_id", "due_at"),
        Index("ix_teacher_assignments_tenant", "tenant_id", "teacher_id"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    class_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teacher_classes.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teacher_sections.id", ondelete="SET NULL"), nullable=True
    )
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, server_default=text("''"), nullable=False)
    assignment_type: Mapped[str] = mapped_column(
        String(24), server_default=text("'assignment'"), nullable=False
    )
    linked_quiz_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    linked_test_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    question_ids_jsonb: Mapped[list[Any]] = mapped_column(
        JSONBVariant, default=list, nullable=False
    )
    max_marks: Mapped[float] = mapped_column(Float, server_default=text("20.0"), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'published'"), nullable=False
    )


class AssignmentSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_asgn_sub_assignment_student"),
        Index("ix_asgn_sub_assignment", "assignment_id", "status"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    assignment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teacher_assignments.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    homework_submission_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    response_text: Mapped[str] = mapped_column(Text, server_default=text("''"), nullable=False)
    ai_suggested_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_feedback_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    teacher_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'submitted'"), nullable=False
    )
    graded_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
