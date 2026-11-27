"""ORM models for Institutional Multi-Tenant Platform (Phase 8 F-003)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.core.outbox import JSONBVariant


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    organization_type: Mapped[str] = mapped_column(
        String(32), server_default=text("'school_group'"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )
    contact_email: Mapped[str] = mapped_column(String(320), nullable=False)
    config_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, default=dict, nullable=False
    )
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class School(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "schools"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_schools_tenant_code"),
        Index("ix_schools_tenant", "tenant_id", "status"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    board_code: Mapped[str] = mapped_column(
        String(32), server_default=text("'CBSE'"), nullable=False
    )
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )
    config_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, default=dict, nullable=False
    )


class Branch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_branches_school_code"),
        Index("ix_branches_tenant_school", "tenant_id", "school_id"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    school_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )


class AcademicYear(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academic_years"
    __table_args__ = (
        UniqueConstraint("school_id", "label", name="uq_academic_years_school_label"),
        Index("ix_academic_years_tenant", "tenant_id", "school_id"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    school_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )


class InstitutionBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "institution_batches"
    __table_args__ = (Index("ix_institution_batches_tenant", "tenant_id", "school_id"),)

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    school_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )
    academic_year_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    grade_label: Mapped[str] = mapped_column(String(40), nullable=False)
    section_name: Mapped[str] = mapped_column(
        String(40), server_default=text("'A'"), nullable=False
    )
    exam_track: Mapped[str] = mapped_column(
        String(40), server_default=text("'cbse_board'"), nullable=False
    )
    capacity: Mapped[int] = mapped_column(Integer, server_default=text("50"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )


class InstitutionMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "institution_memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "member_role", name="uq_inst_member_tenant_user_role"),
        Index("ix_inst_memberships_tenant", "tenant_id", "member_role"),
        Index("ix_inst_memberships_user", "user_id", "status"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    school_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("schools.id", ondelete="SET NULL"), nullable=True
    )
    branch_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    member_role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )


class BatchEnrollment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "batch_enrollments"
    __table_args__ = (
        UniqueConstraint("batch_id", "student_id", name="uq_batch_enrollments_batch_student"),
        Index("ix_batch_enrollments_tenant", "tenant_id", "batch_id"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institution_batches.id", ondelete="CASCADE"),
        nullable=False,
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


class InstitutionAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "institution_assessments"
    __table_args__ = (Index("ix_inst_assessments_tenant", "tenant_id", "school_id"),)

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    school_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institution_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), server_default=text("'test'"), nullable=False)
    linked_test_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_marks: Mapped[float] = mapped_column(Float, server_default=text("100.0"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'published'"), nullable=False
    )
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
