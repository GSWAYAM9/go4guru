"""Core database session, authentication context, RBAC guards, and audit helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.errors import AppError
from src.core.logging import request_id_ctx_var
from src.core.outbox import AuditLog
from src.core.security import decode_access_token

PRIVILEGED_MFA_ROLES: frozenset[str] = frozenset(
    {"platform_admin", "school_admin", "content_admin", "academic_reviewer"}
)

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Verified caller identity and RBAC claim context."""

    id: UUID
    email: str
    roles: tuple[str, ...]
    permissions: frozenset[str]
    tenant_id: UUID | None
    session_id: UUID
    mfa_verified: bool
    is_minor: bool

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    @property
    def requires_mfa(self) -> bool:
        return any(role in PRIVILEGED_MFA_ROLES for role in self.roles)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a transactional async SQLAlchemy session bound to app.state.db."""
    db_manager = request.app.state.db
    async with db_manager.session_factory() as session:
        yield session


def _extract_user_from_token(token: str, settings: Settings) -> AuthenticatedUser:
    try:
        claims = decode_access_token(token, settings=settings)
        user_id = UUID(str(claims["sub"]))
        session_id = UUID(str(claims["sid"]))
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_TOKEN",
            message="Invalid or expired access token.",
        ) from exc

    roles_raw = claims.get("roles")
    if isinstance(roles_raw, list):
        roles = tuple(str(r) for r in roles_raw)
    else:
        roles = (str(claims.get("role", "student")),)

    perms_raw = claims.get("perms")
    permissions = (
        frozenset(str(p) for p in perms_raw) if isinstance(perms_raw, list) else frozenset()
    )
    tenant_raw = claims.get("tenant_id")
    tenant_id = UUID(str(tenant_raw)) if tenant_raw else None

    return AuthenticatedUser(
        id=user_id,
        email=str(claims.get("email", "")),
        roles=roles,
        permissions=permissions,
        tenant_id=tenant_id,
        session_id=session_id,
        mfa_verified=bool(claims.get("mfa_verified", False)),
        is_minor=bool(claims.get("is_minor", False)),
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
) -> AuthenticatedUser:
    """Resolve mandatory authenticated caller or raise 401 UNAUTHENTICATED."""
    if credentials is None or not credentials.credentials:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHENTICATED",
            message="Authentication credentials are required.",
        )
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return _extract_user_from_token(credentials.credentials, settings)


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
) -> AuthenticatedUser | None:
    """Resolve authenticated caller if Bearer header is present, else None."""
    if credentials is None or not credentials.credentials:
        return None
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return _extract_user_from_token(credentials.credentials, settings)


def require_permissions(
    *required_permissions: str,
    allow_unverified_mfa: bool = False,
) -> Callable[[AuthenticatedUser], Coroutine[Any, Any, AuthenticatedUser]]:
    """Enforce backend deny-by-default RBAC permissions and privileged MFA gate."""

    async def _dependency(
        user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    ) -> AuthenticatedUser:
        if not allow_unverified_mfa and user.requires_mfa and not user.mfa_verified:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="MFA_REQUIRED",
                message="Privileged role requires completed TOTP MFA verification.",
            )
        missing = [perm for perm in required_permissions if not user.has_permission(perm)]
        if missing:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FORBIDDEN",
                message="Insufficient permissions for this operation.",
                details={"missing_permissions": missing},
            )
        return user

    return _dependency


def require_any_permission(
    *allowed_permissions: str,
    allow_unverified_mfa: bool = False,
) -> Callable[[AuthenticatedUser], Coroutine[Any, Any, AuthenticatedUser]]:
    """Enforce that caller holds at least one of the specified permissions plus MFA gate."""

    async def _dependency(
        user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    ) -> AuthenticatedUser:
        if not allow_unverified_mfa and user.requires_mfa and not user.mfa_verified:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="MFA_REQUIRED",
                message="Privileged role requires completed TOTP MFA verification.",
            )
        if not any(user.has_permission(perm) for perm in allowed_permissions):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FORBIDDEN",
                message="Insufficient permissions for this operation.",
                details={"required_any_of": list(allowed_permissions)},
            )
        return user

    return _dependency


def require_roles(
    *allowed_roles: str,
    allow_unverified_mfa: bool = False,
) -> Callable[[AuthenticatedUser], Coroutine[Any, Any, AuthenticatedUser]]:
    """Enforce role membership plus privileged MFA gate."""

    async def _dependency(
        user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    ) -> AuthenticatedUser:
        if not allow_unverified_mfa and user.requires_mfa and not user.mfa_verified:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="MFA_REQUIRED",
                message="Privileged role requires completed TOTP MFA verification.",
            )
        if not any(user.has_role(role) for role in allowed_roles):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FORBIDDEN",
                message="Role does not permit this operation.",
            )
        return user

    return _dependency


def write_audit_log(
    db: AsyncSession,
    *,
    actor_id: UUID | None,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    tenant_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append an immutable AuditLog entry inside the caller's DB transaction."""
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id_ctx_var.get(),
            metadata_jsonb=metadata or {},
        )
    )
