"""Phase 0 security baseline utilities: Argon2id, JWT, and spreadsheet sanitization."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.core.config import Settings, get_settings

ALLOWED_JWT_ALGORITHMS: tuple[str, ...] = ("HS256", "RS256")
_FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")


def build_password_hasher(settings: Settings | None = None) -> PasswordHasher:
    """Create configured Argon2id PasswordHasher."""
    cfg = settings or get_settings()
    return PasswordHasher(
        time_cost=cfg.password_argon2_time_cost,
        memory_cost=cfg.password_argon2_memory_cost,
        parallelism=cfg.password_argon2_parallelism,
    )


def hash_password(plain_password: str, settings: Settings | None = None) -> str:
    """Hash a password with Argon2id; rejects empty passwords."""
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    return build_password_hasher(settings).hash(plain_password)


def verify_password(
    plain_password: str, password_hash: str, settings: Settings | None = None
) -> bool:
    """Verify a plaintext password against an Argon2id hash in constant time."""
    if not plain_password or not password_hash:
        return False
    try:
        return build_password_hasher(settings).verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(
    *,
    subject: str,
    role: str,
    tenant_id: str | None = None,
    extra_claims: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> str:
    """Issue a short-lived signed JWT using an explicitly pinned algorithm."""
    cfg = settings or get_settings()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=cfg.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if extra_claims:
        for key, val in extra_claims.items():
            if key not in {"sub", "role", "jti", "iat", "exp", "type"}:
                payload[key] = val
    return jwt.encode(
        payload,
        cfg.jwt_secret_key.get_secret_value(),
        algorithm=cfg.jwt_algorithm,
    )


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """Decode and validate an access JWT against the pinned algorithm allowlist."""
    cfg = settings or get_settings()
    if cfg.jwt_algorithm not in ALLOWED_JWT_ALGORITHMS:
        raise ValueError("Unsupported JWT algorithm configured.")
    decoded: dict[str, Any] = jwt.decode(
        token,
        cfg.jwt_secret_key.get_secret_value(),
        algorithms=[cfg.jwt_algorithm],
        options={"require": ["sub", "exp", "iat", "jti", "type"]},
    )
    if decoded.get("type") != "access":
        raise jwt.InvalidTokenError("Token type must be access.")
    return decoded


def sanitize_spreadsheet_cell(value: str) -> str:
    """Neutralize Excel/CSV formula injection prefixes per EXCEL_IMPORT_SPECIFICATION.md."""
    if value and value.startswith(_FORMULA_PREFIXES):
        return f"'{value}"
    return value
