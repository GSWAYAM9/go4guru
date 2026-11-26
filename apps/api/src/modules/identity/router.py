"""HTTP API routers for auth, profiles, RBAC administration, and audit logs."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import (
    AuthenticatedUser,
    get_current_user,
    get_db_session,
    require_permissions,
)
from src.core.config import Settings, get_settings
from src.core.errors import AppError
from src.modules.identity.repository import IdentityRepository
from src.modules.identity.schemas import (
    AssignRoleRequest,
    AuditLogEntry,
    AuthTokenResponse,
    LoginRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    SessionInfo,
    StudentProfileResponse,
    StudentProfileUpdateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from src.modules.identity.service import IdentityService

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/v1/users", tags=["users"])
admin_identity_router = APIRouter(prefix="/api/v1/admin", tags=["admin-identity"])


def _set_refresh_cookie(response: Response, refresh_token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure or settings.app_env in {"staging", "production"},
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    return ip, ua


@auth_router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AuthTokenResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    ip, ua = _client_meta(request)
    svc = IdentityService(db, settings)
    auth_resp, raw_refresh = await svc.register(payload, ip_addr=ip, user_agent=ua)
    _set_refresh_cookie(response, raw_refresh, settings)
    return auth_resp


@auth_router.post("/login", response_model=AuthTokenResponse)
async def login_user(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AuthTokenResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    ip, ua = _client_meta(request)
    svc = IdentityService(db, settings)
    auth_resp, raw_refresh = await svc.login(payload, ip_addr=ip, user_agent=ua)
    _set_refresh_cookie(response, raw_refresh, settings)
    return auth_resp


@auth_router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_session(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AuthTokenResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    raw_refresh = (
        payload.refresh_token if payload and payload.refresh_token else None
    ) or request.cookies.get(settings.refresh_cookie_name)
    ip, ua = _client_meta(request)
    svc = IdentityService(db, settings)
    auth_resp, next_refresh = await svc.refresh(raw_refresh, ip_addr=ip, user_agent=ua)
    _set_refresh_cookie(response, next_refresh, settings)
    return auth_resp


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    request: Request,
    response: Response,
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> None:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    svc = IdentityService(db, settings)
    await svc.logout(caller)
    response.delete_cookie(key=settings.refresh_cookie_name, path="/api/v1/auth")


@auth_router.post("/mfa/setup", response_model=MfaSetupResponse)
async def setup_mfa(
    request: Request,
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> MfaSetupResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    svc = IdentityService(db, settings)
    return await svc.setup_mfa(caller)


@auth_router.post("/mfa/verify", response_model=AuthTokenResponse)
async def verify_mfa(
    payload: MfaVerifyRequest,
    request: Request,
    response: Response,
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AuthTokenResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    ip, ua = _client_meta(request)
    svc = IdentityService(db, settings)
    auth_resp, raw_refresh = await svc.verify_mfa(caller, payload.code, ip_addr=ip, user_agent=ua)
    _set_refresh_cookie(response, raw_refresh, settings)
    return auth_resp


@auth_router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[SessionInfo]:
    sessions = await IdentityRepository(db).list_user_sessions(caller.id)
    return [
        SessionInfo(
            id=s.id,
            mfa_verified=s.mfa_verified,
            user_agent=s.user_agent,
            created_at=s.created_at,
            expires_at=s.expires_at,
            revoked_at=s.revoked_at,
        )
        for s in sessions
    ]


@auth_router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> None:
    repo = IdentityRepository(db)
    target = await repo.get_session_by_id(session_id)
    if target is None or target.user_id != caller.id:
        raise AppError(status_code=404, code="SESSION_NOT_FOUND", message="Session not found.")
    from datetime import UTC, datetime

    target.revoked_at = datetime.now(UTC)
    await db.commit()


@users_router.get("/me", response_model=UserProfileResponse)
async def get_me(
    request: Request,
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> UserProfileResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await IdentityService(db, settings).get_me_profile(caller)


@users_router.patch("/me/profile", response_model=UserProfileResponse)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    request: Request,
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> UserProfileResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await IdentityService(db, settings).update_me_profile(caller, payload)


@users_router.get("/me/student-profile", response_model=StudentProfileResponse)
async def get_my_student_profile(
    request: Request,
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> StudentProfileResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await IdentityService(db, settings).get_student_profile(caller)


@users_router.put("/me/student-profile", response_model=StudentProfileResponse)
async def update_my_student_profile(
    payload: StudentProfileUpdateRequest,
    request: Request,
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> StudentProfileResponse:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return await IdentityService(db, settings).update_student_profile(caller, payload)


@admin_identity_router.post("/users/roles", response_model=dict[str, list[str]])
async def assign_role_to_user(
    payload: AssignRoleRequest,
    request: Request,
    caller: AuthenticatedUser = Depends(require_permissions("admin:users_manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, list[str]]:
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    roles = await IdentityService(db, settings).assign_role(caller, payload)
    return {"roles": roles}


@admin_identity_router.get("/audit-logs", response_model=list[AuditLogEntry])
async def list_audit_logs(
    limit: int = 50,
    caller: AuthenticatedUser = Depends(require_permissions("admin:audit_read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[AuditLogEntry]:
    bounded = max(1, min(limit, 200))
    logs = await IdentityRepository(db).list_audit_logs(limit=bounded)
    return [
        AuditLogEntry(
            id=entry.id,
            tenant_id=entry.tenant_id,
            actor_id=entry.actor_id,
            actor_role=entry.actor_role,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            request_id=entry.request_id,
            metadata_jsonb=entry.metadata_jsonb,
            created_at=entry.created_at,
        )
        for entry in logs
    ]
