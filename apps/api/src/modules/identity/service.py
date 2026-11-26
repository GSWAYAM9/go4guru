"""Business logic service for auth, MFA, session rotation, RBAC, and profiles."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pyotp
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import PRIVILEGED_MFA_ROLES, AuthenticatedUser, write_audit_log
from src.core.config import Settings
from src.core.errors import AppError
from src.core.security import create_access_token, hash_password, verify_password
from src.modules.identity.models import AuthSession, StudentProfile, User, UserProfile
from src.modules.identity.repository import IdentityRepository
from src.modules.identity.schemas import (
    AssignRoleRequest,
    AuthTokenResponse,
    LoginRequest,
    MfaSetupResponse,
    RegisterRequest,
    StudentProfileResponse,
    StudentProfileUpdateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserSummary,
)


def _hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _hash_ip(ip_addr: str | None) -> str | None:
    if not ip_addr:
        return None
    return hashlib.sha256(ip_addr.encode("utf-8")).hexdigest()[:32]


class IdentityService:
    """Implements authentication, MFA, rotating sessions, and profile workflows."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repo = IdentityRepository(db)

    def _issue_access_jwt(
        self,
        *,
        user: User,
        roles: list[str],
        permissions: list[str],
        tenant_id: UUID | None,
        session_id: UUID,
        mfa_verified: bool,
    ) -> str:
        primary_role = roles[0] if roles else "student"
        return create_access_token(
            subject=str(user.id),
            role=primary_role,
            tenant_id=str(tenant_id) if tenant_id else None,
            extra_claims={
                "email": user.email,
                "roles": roles,
                "perms": permissions,
                "sid": str(session_id),
                "mfa_verified": mfa_verified,
                "is_minor": user.is_minor,
            },
            settings=self.settings,
        )

    async def _create_session_and_response(
        self,
        *,
        user: User,
        display_name: str,
        roles: list[str],
        permissions: list[str],
        tenant_id: UUID | None,
        mfa_verified: bool,
        token_family_id: UUID | None,
        ip_addr: str | None,
        user_agent: str | None,
    ) -> tuple[AuthTokenResponse, str]:
        raw_refresh = secrets.token_urlsafe(48)
        now = datetime.now(UTC)
        family_id = token_family_id or uuid4()
        session = AuthSession(
            user_id=user.id,
            refresh_token_hash=_hash_refresh_token(raw_refresh),
            token_family_id=family_id,
            ip_hash=_hash_ip(ip_addr),
            user_agent=(user_agent or "")[:256] or None,
            mfa_verified=mfa_verified,
            expires_at=now + timedelta(days=self.settings.jwt_refresh_token_expire_days),
        )
        self.db.add(session)
        await self.db.flush()

        requires_mfa = any(role in PRIVILEGED_MFA_ROLES for role in roles)
        access_token = self._issue_access_jwt(
            user=user,
            roles=roles,
            permissions=permissions,
            tenant_id=tenant_id,
            session_id=session.id,
            mfa_verified=mfa_verified,
        )
        response = AuthTokenResponse(
            access_token=access_token,
            expires_in_seconds=self.settings.jwt_access_token_expire_minutes * 60,
            mfa_required=requires_mfa and not mfa_verified,
            mfa_verified=mfa_verified,
            user=UserSummary(
                id=user.id,
                email=user.email,
                display_name=display_name,
                roles=roles,
                permissions=permissions,
                is_minor=user.is_minor,
                mfa_enabled=user.mfa_enabled,
                mfa_verified=mfa_verified,
                status=user.status,
            ),
        )
        return response, raw_refresh

    async def register(
        self,
        payload: RegisterRequest,
        *,
        ip_addr: str | None,
        user_agent: str | None,
    ) -> tuple[AuthTokenResponse, str]:
        email_norm = payload.email.lower().strip()
        existing = await self.repo.get_user_by_email(email_norm)
        if existing is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="EMAIL_ALREADY_REGISTERED",
                message="An account with this email already exists.",
            )

        role = await self.repo.get_role_by_code(payload.role)
        if role is None:
            raise AppError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code="ROLE_SEED_MISSING",
                message="Requested role is not provisioned.",
            )

        current_year = datetime.now(UTC).year
        is_minor = (
            payload.date_of_birth_year is not None
            and (current_year - payload.date_of_birth_year) < 18
        )
        user = User(
            email=email_norm,
            password_hash=hash_password(payload.password, settings=self.settings),
            status="active",
            date_of_birth_year=payload.date_of_birth_year,
            is_minor=is_minor,
            last_login_at=datetime.now(UTC),
        )
        self.db.add(user)
        await self.db.flush()

        profile = UserProfile(user_id=user.id, display_name=payload.display_name.strip())
        self.db.add(profile)

        if payload.role == "student":
            self.db.add(StudentProfile(user_id=user.id))

        await self.repo.assign_role_if_missing(user_id=user.id, role_id=role.id)
        roles, permissions, tenant_id = await self.repo.get_user_roles_and_permissions(user.id)

        write_audit_log(
            self.db,
            actor_id=user.id,
            actor_role=payload.role,
            action="auth.register",
            resource_type="user",
            resource_id=str(user.id),
            metadata={"role": payload.role, "is_minor": is_minor},
        )
        result = await self._create_session_and_response(
            user=user,
            display_name=profile.display_name,
            roles=roles,
            permissions=permissions,
            tenant_id=tenant_id,
            mfa_verified=False,
            token_family_id=None,
            ip_addr=ip_addr,
            user_agent=user_agent,
        )
        await self.db.commit()
        return result

    async def login(
        self,
        payload: LoginRequest,
        *,
        ip_addr: str | None,
        user_agent: str | None,
    ) -> tuple[AuthTokenResponse, str]:
        user = await self.repo.get_user_by_email(payload.email.lower().strip())
        if user is None or not verify_password(
            payload.password, user.password_hash, settings=self.settings
        ):
            write_audit_log(
                self.db,
                actor_id=user.id if user else None,
                actor_role="anonymous",
                action="auth.login_failed",
                resource_type="user",
                resource_id=str(user.id) if user else None,
            )
            await self.db.commit()
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_CREDENTIALS",
                message="Invalid email or password.",
            )

        if user.status != "active":
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="ACCOUNT_INACTIVE",
                message="User account is not active.",
            )

        roles, permissions, tenant_id = await self.repo.get_user_roles_and_permissions(user.id)
        requires_mfa = any(role in PRIVILEGED_MFA_ROLES for role in roles)
        mfa_verified = False

        if user.mfa_enabled and user.mfa_secret and payload.totp_code:
            totp = pyotp.TOTP(user.mfa_secret)
            if not totp.verify(payload.totp_code.strip(), valid_window=1):
                write_audit_log(
                    self.db,
                    actor_id=user.id,
                    actor_role=roles[0] if roles else "student",
                    action="auth.mfa_failed",
                    resource_type="user",
                    resource_id=str(user.id),
                )
                await self.db.commit()
                raise AppError(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    code="INVALID_MFA_CODE",
                    message="Invalid TOTP authenticator code.",
                )
            mfa_verified = True
        elif not requires_mfa:
            mfa_verified = True

        user.last_login_at = datetime.now(UTC)
        profile = await self.repo.get_profile(user.id)
        display_name = profile.display_name if profile else user.email

        write_audit_log(
            self.db,
            actor_id=user.id,
            actor_role=roles[0] if roles else "student",
            action="auth.login",
            resource_type="user",
            resource_id=str(user.id),
            metadata={"mfa_verified": mfa_verified},
        )
        result = await self._create_session_and_response(
            user=user,
            display_name=display_name,
            roles=roles,
            permissions=permissions,
            tenant_id=tenant_id,
            mfa_verified=mfa_verified,
            token_family_id=None,
            ip_addr=ip_addr,
            user_agent=user_agent,
        )
        await self.db.commit()
        return result

    async def refresh(
        self,
        raw_refresh_token: str | None,
        *,
        ip_addr: str | None,
        user_agent: str | None,
    ) -> tuple[AuthTokenResponse, str]:
        if not raw_refresh_token:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="REFRESH_TOKEN_MISSING",
                message="Refresh token is required.",
            )

        session = await self.repo.get_session_by_refresh_hash(
            _hash_refresh_token(raw_refresh_token)
        )
        if session is None:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_REFRESH_TOKEN",
                message="Invalid refresh token.",
            )

        now = datetime.now(UTC)
        if session.revoked_at is not None:
            await self.repo.revoke_token_family(session.token_family_id)
            write_audit_log(
                self.db,
                actor_id=session.user_id,
                actor_role="user",
                action="auth.refresh_reuse_detected",
                resource_type="session",
                resource_id=str(session.id),
                metadata={"token_family_id": str(session.token_family_id)},
            )
            await self.db.commit()
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="REFRESH_TOKEN_REUSED",
                message="Refresh token reuse detected; session family revoked.",
            )

        if session.expires_at <= now:
            session.revoked_at = now
            await self.db.commit()
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="REFRESH_TOKEN_EXPIRED",
                message="Refresh token has expired.",
            )

        user = await self.repo.get_user_by_id(session.user_id)
        if user is None or user.status != "active":
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_USER",
                message="User account unavailable.",
            )

        session.revoked_at = now
        roles, permissions, tenant_id = await self.repo.get_user_roles_and_permissions(user.id)
        profile = await self.repo.get_profile(user.id)
        display_name = profile.display_name if profile else user.email

        result = await self._create_session_and_response(
            user=user,
            display_name=display_name,
            roles=roles,
            permissions=permissions,
            tenant_id=tenant_id,
            mfa_verified=session.mfa_verified,
            token_family_id=session.token_family_id,
            ip_addr=ip_addr,
            user_agent=user_agent,
        )
        await self.db.commit()
        return result

    async def logout(self, caller: AuthenticatedUser) -> None:
        session = await self.repo.get_session_by_id(caller.session_id)
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            write_audit_log(
                self.db,
                actor_id=caller.id,
                actor_role=caller.roles[0] if caller.roles else "user",
                action="auth.logout",
                resource_type="session",
                resource_id=str(session.id),
            )
            await self.db.commit()

    async def setup_mfa(self, caller: AuthenticatedUser) -> MfaSetupResponse:
        user = await self.repo.get_user_by_id(caller.id)
        if user is None:
            raise AppError(status_code=404, code="USER_NOT_FOUND", message="User not found.")

        secret = pyotp.random_base32()
        user.mfa_secret = secret
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name="Go4Guru")
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0] if caller.roles else "user",
            action="auth.mfa_setup_initiated",
            resource_type="user",
            resource_id=str(user.id),
        )
        await self.db.commit()
        return MfaSetupResponse(secret=secret, provisioning_uri=uri)

    async def verify_mfa(
        self,
        caller: AuthenticatedUser,
        code: str,
        *,
        ip_addr: str | None,
        user_agent: str | None,
    ) -> tuple[AuthTokenResponse, str]:
        user = await self.repo.get_user_by_id(caller.id)
        if user is None or not user.mfa_secret:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="MFA_NOT_CONFIGURED",
                message="Run MFA setup before verification.",
            )
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(code.strip(), valid_window=1):
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_MFA_CODE",
                message="Invalid TOTP authenticator code.",
            )
        user.mfa_enabled = True

        old_session = await self.repo.get_session_by_id(caller.session_id)
        if old_session is not None and old_session.revoked_at is None:
            old_session.revoked_at = datetime.now(UTC)

        roles, permissions, tenant_id = await self.repo.get_user_roles_and_permissions(user.id)
        profile = await self.repo.get_profile(user.id)
        display_name = profile.display_name if profile else user.email

        write_audit_log(
            self.db,
            actor_id=user.id,
            actor_role=roles[0] if roles else "user",
            action="auth.mfa_verified",
            resource_type="user",
            resource_id=str(user.id),
        )
        result = await self._create_session_and_response(
            user=user,
            display_name=display_name,
            roles=roles,
            permissions=permissions,
            tenant_id=tenant_id,
            mfa_verified=True,
            token_family_id=old_session.token_family_id if old_session else None,
            ip_addr=ip_addr,
            user_agent=user_agent,
        )
        await self.db.commit()
        return result

    async def get_me_profile(self, caller: AuthenticatedUser) -> UserProfileResponse:
        user = await self.repo.get_user_by_id(caller.id)
        profile = await self.repo.get_profile(caller.id)
        if user is None or profile is None:
            raise AppError(status_code=404, code="USER_NOT_FOUND", message="User not found.")
        roles, permissions, _ = await self.repo.get_user_roles_and_permissions(caller.id)
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            status=user.status,
            is_minor=user.is_minor,
            mfa_enabled=user.mfa_enabled,
            roles=roles,
            permissions=permissions,
            display_name=profile.display_name,
            avatar_url=profile.avatar_url,
            timezone=profile.timezone,
            ui_language=profile.ui_language,
            preferred_explanation_language=profile.preferred_explanation_language,
            preferred_voice_language=profile.preferred_voice_language,
            preferred_subtitle_language=profile.preferred_subtitle_language,
            preferred_question_language=profile.preferred_question_language,
            preferred_answer_language=profile.preferred_answer_language,
        )

    async def update_me_profile(
        self, caller: AuthenticatedUser, payload: UserProfileUpdateRequest
    ) -> UserProfileResponse:
        profile = await self.repo.get_profile(caller.id)
        if profile is None:
            raise AppError(status_code=404, code="PROFILE_NOT_FOUND", message="Profile not found.")
        for field, val in payload.model_dump(exclude_unset=True).items():
            if val is not None:
                setattr(profile, field, val)
        await self.db.commit()
        return await self.get_me_profile(caller)

    async def get_student_profile(self, caller: AuthenticatedUser) -> StudentProfileResponse:
        sp = await self.repo.get_student_profile(caller.id)
        if sp is None:
            sp = StudentProfile(user_id=caller.id)
            self.db.add(sp)
            await self.db.commit()
            await self.db.refresh(sp)
        return StudentProfileResponse(
            user_id=sp.user_id,
            board_id=sp.board_id,
            academic_session_id=sp.academic_session_id,
            grade_id=sp.grade_id,
            curriculum_version_id=sp.curriculum_version_id,
            primary_exam_target=sp.primary_exam_target,
            daily_study_minutes_target=sp.daily_study_minutes_target,
            onboarding_completed_at=sp.onboarding_completed_at,
        )

    async def update_student_profile(
        self, caller: AuthenticatedUser, payload: StudentProfileUpdateRequest
    ) -> StudentProfileResponse:
        sp = await self.repo.get_student_profile(caller.id)
        if sp is None:
            sp = StudentProfile(user_id=caller.id)
            self.db.add(sp)

        sp.board_id = payload.board_id
        sp.academic_session_id = payload.academic_session_id
        sp.grade_id = payload.grade_id
        sp.curriculum_version_id = payload.curriculum_version_id
        sp.primary_exam_target = payload.primary_exam_target
        sp.daily_study_minutes_target = payload.daily_study_minutes_target
        if payload.grade_id is not None:
            sp.onboarding_completed_at = datetime.now(UTC)

        await self.db.commit()
        return await self.get_student_profile(caller)

    async def assign_role(self, caller: AuthenticatedUser, payload: AssignRoleRequest) -> list[str]:
        target_user = await self.repo.get_user_by_id(payload.user_id)
        if target_user is None:
            raise AppError(status_code=404, code="USER_NOT_FOUND", message="Target user not found.")
        role = await self.repo.get_role_by_code(payload.role_code)
        if role is None:
            raise AppError(status_code=404, code="ROLE_NOT_FOUND", message="Role not found.")

        await self.repo.assign_role_if_missing(
            user_id=target_user.id,
            role_id=role.id,
            tenant_id=payload.tenant_id,
            granted_by=caller.id,
        )
        write_audit_log(
            self.db,
            actor_id=caller.id,
            actor_role=caller.roles[0] if caller.roles else "platform_admin",
            action="rbac.role_assigned",
            resource_type="user",
            resource_id=str(target_user.id),
            metadata={"role_code": payload.role_code},
        )
        await self.db.commit()
        roles, _, _ = await self.repo.get_user_roles_and_permissions(target_user.id)
        return roles
