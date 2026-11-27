"""ORM models for identity, RBAC, sessions, and student profiles."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Core user account record."""

    __tablename__ = "users"

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default=text("'active'"), nullable=False)
    date_of_birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_minor: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserProfile(TimestampMixin, Base):
    """User display identity and 6 independent multilingual preferences."""

    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(64), server_default=text("'Asia/Kolkata'"), nullable=False
    )
    ui_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    preferred_explanation_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    preferred_voice_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    preferred_subtitle_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    preferred_question_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    preferred_answer_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    bilingual_explanation_mode: Mapped[str] = mapped_column(
        String(32), server_default=text("'bilingual_stem_en'"), nullable=False
    )


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Canonical platform RBAC role."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=False)


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Fine-grained RBAC permission code."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(48), nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False)


class RolePermission(Base):
    """Join mapping between roles and permissions."""

    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class UserRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Role assignment granted to a user (optionally scoped to tenant_id)."""

    __tablename__ = "user_roles"
    __table_args__ = (Index("ix_user_roles_user_active", "user_id", "revoked_at"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    granted_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Rotating refresh token session state with reuse detection via token_family_id."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_family", "user_id", "token_family_id"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    token_family_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    mfa_verified: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StudentProfile(TimestampMixin, Base):
    """Academic onboarding configuration for learners."""

    __tablename__ = "student_profiles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    board_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    academic_session_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    grade_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    curriculum_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    primary_exam_target: Mapped[str] = mapped_column(
        String(32), server_default=text("'cbse_board'"), nullable=False
    )
    daily_study_minutes_target: Mapped[int] = mapped_column(
        Integer, server_default=text("60"), nullable=False
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


_UTC_NOW = func.now()
