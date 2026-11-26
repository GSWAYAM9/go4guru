"""Async SQLAlchemy repository for identity, RBAC, sessions, and audit logs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.outbox import AuditLog
from src.modules.identity.models import (
    AuthSession,
    Permission,
    Role,
    RolePermission,
    StudentProfile,
    User,
    UserProfile,
    UserRole,
)


class IdentityRepository:
    """Data-access layer for identity & RBAC entities."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
        return await self.db.scalar(stmt)

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        return await self.db.scalar(stmt)

    async def get_profile(self, user_id: UUID) -> UserProfile | None:
        return await self.db.get(UserProfile, user_id)

    async def get_student_profile(self, user_id: UUID) -> StudentProfile | None:
        return await self.db.get(StudentProfile, user_id)

    async def get_role_by_code(self, code: str) -> Role | None:
        stmt = select(Role).where(Role.code == code)
        return await self.db.scalar(stmt)

    async def get_user_roles_and_permissions(
        self, user_id: UUID
    ) -> tuple[list[str], list[str], UUID | None]:
        role_stmt = (
            select(Role.id, Role.code, UserRole.tenant_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, UserRole.revoked_at.is_(None))
        )
        rows = (await self.db.execute(role_stmt)).all()
        if not rows:
            return [], [], None

        role_ids = [r[0] for r in rows]
        role_codes = sorted({r[1] for r in rows})
        tenant_id = next((r[2] for r in rows if r[2] is not None), None)

        perm_stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(role_ids))
        )
        perm_codes = sorted(set((await self.db.scalars(perm_stmt)).all()))
        return role_codes, perm_codes, tenant_id

    async def get_session_by_refresh_hash(self, token_hash: str) -> AuthSession | None:
        stmt = select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
        return await self.db.scalar(stmt)

    async def get_session_by_id(self, session_id: UUID) -> AuthSession | None:
        return await self.db.get(AuthSession, session_id)

    async def list_user_sessions(self, user_id: UUID) -> list[AuthSession]:
        stmt = (
            select(AuthSession)
            .where(AuthSession.user_id == user_id)
            .order_by(AuthSession.created_at.desc())
            .limit(20)
        )
        return list((await self.db.scalars(stmt)).all())

    async def revoke_token_family(self, token_family_id: UUID) -> None:
        now = datetime.now(UTC)
        stmt = (
            update(AuthSession)
            .where(
                and_(
                    AuthSession.token_family_id == token_family_id,
                    AuthSession.revoked_at.is_(None),
                )
            )
            .values(revoked_at=now)
        )
        await self.db.execute(stmt)

    async def assign_role_if_missing(
        self,
        *,
        user_id: UUID,
        role_id: UUID,
        tenant_id: UUID | None = None,
        granted_by: UUID | None = None,
    ) -> UserRole:
        existing_stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.revoked_at.is_(None),
        )
        existing = await self.db.scalar(existing_stmt)
        if existing is not None:
            return existing
        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
            tenant_id=tenant_id,
            granted_by=granted_by,
        )
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def list_audit_logs(self, *, limit: int = 50) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        return list((await self.db.scalars(stmt)).all())
