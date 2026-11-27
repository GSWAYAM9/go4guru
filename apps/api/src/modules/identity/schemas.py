"""Pydantic v2 DTO schemas for authentication, RBAC, MFA, and profiles."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

ExamTarget = Literal["cbse_board", "jee_main", "jee_advanced", "neet", "foundation"]
RoleCode = Literal[
    "student",
    "parent",
    "teacher",
    "mentor",
    "school_admin",
    "content_admin",
    "academic_reviewer",
    "platform_admin",
]


def _validate_password_strength(value: str) -> str:
    if len(value) < 8 or len(value) > 128:
        raise ValueError("Password must be between 8 and 128 characters.")
    if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
        raise ValueError("Password must include at least one letter and one digit.")
    return value


class RegisterRequest(BaseModel):
    """Public account registration payload (restricted to student/parent roles)."""

    email: EmailStr
    password: str
    display_name: str = Field(min_length=2, max_length=120)
    date_of_birth_year: int | None = Field(default=None, ge=1940, le=2025)
    role: Literal["student", "parent"] = "student"

    @field_validator("password")
    @classmethod
    def check_password(cls, val: str) -> str:
        return _validate_password_strength(val)


class LoginRequest(BaseModel):
    """Password login payload with optional TOTP MFA code."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    totp_code: str | None = Field(default=None, min_length=6, max_length=8)


class RefreshRequest(BaseModel):
    """Optional JSON refresh token body (cookie takes precedence when sent)."""

    refresh_token: str | None = None


class UserSummary(BaseModel):
    """Public summary of authenticated caller."""

    id: UUID
    email: EmailStr
    display_name: str
    roles: list[str]
    permissions: list[str]
    is_minor: bool
    mfa_enabled: bool
    mfa_verified: bool
    status: str


class AuthTokenResponse(BaseModel):
    """Issued access token + authentication state."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in_seconds: int
    mfa_required: bool
    mfa_verified: bool
    user: UserSummary


class MfaSetupResponse(BaseModel):
    """TOTP provisioning secret & otpauth URI for authenticator apps."""

    secret: str
    provisioning_uri: str


class MfaVerifyRequest(BaseModel):
    """6-digit TOTP verification code."""

    code: str = Field(min_length=6, max_length=8)


class SessionInfo(BaseModel):
    """Active refresh session record."""

    id: UUID
    mfa_verified: bool
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class UserProfileResponse(BaseModel):
    """Full profile view combining user, display profile, roles, and permissions."""

    id: UUID
    email: EmailStr
    status: str
    is_minor: bool
    mfa_enabled: bool
    roles: list[str]
    permissions: list[str]
    display_name: str
    avatar_url: str | None
    timezone: str
    ui_language: str
    preferred_explanation_language: str
    preferred_voice_language: str
    preferred_subtitle_language: str
    preferred_question_language: str
    preferred_answer_language: str
    bilingual_explanation_mode: str = "bilingual_stem_en"


class UserProfileUpdateRequest(BaseModel):
    """Partial update of display and language preferences."""

    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    ui_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_explanation_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_voice_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_subtitle_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_question_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_answer_language: str | None = Field(default=None, min_length=2, max_length=16)
    bilingual_explanation_mode: (
        Literal["monolingual", "bilingual_stem_en", "side_by_side"] | None
    ) = None


class StudentProfileResponse(BaseModel):
    """Student academic profile & onboarding state."""

    user_id: UUID
    board_id: UUID | None
    academic_session_id: UUID | None
    grade_id: UUID | None
    curriculum_version_id: UUID | None
    primary_exam_target: str
    daily_study_minutes_target: int
    onboarding_completed_at: datetime | None


class StudentProfileUpdateRequest(BaseModel):
    """Student onboarding / target update payload."""

    board_id: UUID | None = None
    academic_session_id: UUID | None = None
    grade_id: UUID | None = None
    curriculum_version_id: UUID | None = None
    primary_exam_target: ExamTarget = "cbse_board"
    daily_study_minutes_target: int = Field(default=60, ge=10, le=720)


class AssignRoleRequest(BaseModel):
    """Platform-admin role assignment payload."""

    user_id: UUID
    role_code: RoleCode
    tenant_id: UUID | None = None


class AuditLogEntry(BaseModel):
    """Immutable audit log read schema."""

    id: UUID
    tenant_id: UUID | None
    actor_id: UUID | None
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None
    request_id: str | None
    metadata_jsonb: dict[str, Any]
    created_at: datetime
