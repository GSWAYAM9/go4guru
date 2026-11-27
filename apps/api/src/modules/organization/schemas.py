"""Pydantic v2 schemas for Institutional Multi-Tenant Platform (Phase 8 F-003)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class OrganizationCreateRequest(BaseModel):
    slug: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=200)
    organization_type: Literal[
        "school_group", "coaching_institute", "standalone_school"
    ] = "school_group"
    contact_email: EmailStr
    plan_code: str = Field(default="school_starter", max_length=48)


class OrganizationConfigUpdateRequest(BaseModel):
    default_language: str | None = Field(default=None, max_length=16)
    allow_ai_tutor: bool | None = None
    allow_homework_ai: bool | None = None
    require_mfa_for_admins: bool | None = None
    allow_parent_portal: bool | None = None


class OrganizationResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    organization_type: str
    status: str
    contact_email: str
    config: dict[str, Any]
    plan_code: str | None = None
    plan_name: str | None = None
    subscription_status: str | None = None
    seat_limit: int = 0
    max_teachers: int = 0
    max_branches: int = 0
    entitlements: dict[str, bool] = Field(default_factory=dict)
    created_at: datetime


class SchoolCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=200)
    board_code: str = Field(default="CBSE", max_length=32)
    city: str | None = Field(default=None, max_length=100)


class SchoolConfigUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    board_code: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=100)
    config: dict[str, Any] | None = None


class SchoolResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    board_code: str
    city: str | None
    status: str
    config: dict[str, Any]
    branches_count: int = 0
    batches_count: int = 0
    created_at: datetime


class BranchCreateRequest(BaseModel):
    school_id: UUID
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    address: str | None = Field(default=None, max_length=500)


class BranchResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    school_id: UUID
    code: str
    name: str
    address: str | None
    status: str
    created_at: datetime


class AcademicYearCreateRequest(BaseModel):
    school_id: UUID
    label: str = Field(min_length=4, max_length=32)
    starts_on: date
    ends_on: date
    is_current: bool = True


class AcademicYearResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    school_id: UUID
    label: str
    starts_on: date
    ends_on: date
    is_current: bool


class BatchCreateRequest(BaseModel):
    school_id: UUID
    branch_id: UUID | None = None
    academic_year_id: UUID | None = None
    name: str = Field(min_length=2, max_length=160)
    grade_label: str = Field(min_length=1, max_length=40)
    section_name: str = Field(default="A", max_length=40)
    exam_track: str = Field(default="cbse_board", max_length=40)
    capacity: int = Field(default=50, ge=1, le=500)


class BatchResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    school_id: UUID
    branch_id: UUID | None
    academic_year_id: UUID | None
    name: str
    grade_label: str
    section_name: str
    exam_track: str
    capacity: int
    status: str
    enrolled_count: int = 0


class InstitutionMemberAddRequest(BaseModel):
    user_email: EmailStr
    member_role: Literal["school_admin", "teacher", "mentor", "student"]
    school_id: UUID | None = None
    branch_id: UUID | None = None


class InstitutionMemberResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    school_id: UUID | None
    branch_id: UUID | None
    user_id: UUID
    user_name: str
    user_email: str
    member_role: str
    status: str
    created_at: datetime


class BatchEnrollStudentRequest(BaseModel):
    student_email: EmailStr
    roll_no: str | None = Field(default=None, max_length=32)


class BatchEnrollmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    batch_id: UUID
    student_id: UUID
    student_name: str
    student_email: str
    roll_no: str | None
    status: str
    enrolled_at: datetime


class InstitutionAssessmentCreateRequest(BaseModel):
    school_id: UUID
    batch_id: UUID | None = None
    title: str = Field(min_length=3, max_length=200)
    kind: Literal["assignment", "test"] = "test"
    due_at: datetime | None = None
    max_marks: float = Field(default=100.0, gt=0, le=1000)


class InstitutionAssessmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    school_id: UUID
    batch_id: UUID | None
    title: str
    kind: str
    due_at: datetime | None
    max_marks: float
    status: str
    created_at: datetime


class InstitutionSchoolSummaryRow(BaseModel):
    school_id: UUID
    school_name: str
    board_code: str
    branches_count: int
    batches_count: int
    assessments_count: int


class InstitutionReportResponse(BaseModel):
    tenant_id: UUID
    organization_name: str
    plan_code: str
    subscription_status: str
    schools_count: int
    branches_count: int
    max_branches: int
    batches_count: int
    teachers_count: int
    max_teachers: int
    mentors_count: int
    students_count: int
    seat_limit: int
    seat_utilization_pct: float
    assessments_count: int
    average_student_practice_accuracy_pct: float
    average_student_mastery_pct: float
    schools_breakdown: list[InstitutionSchoolSummaryRow]
    generated_at: datetime
