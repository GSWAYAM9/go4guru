"""Unit tests for Phase 0 configuration invariants and security baseline."""

from __future__ import annotations

import jwt
import pytest
from pydantic import ValidationError
from src.core.config import Settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    sanitize_spreadsheet_cell,
    verify_password,
)


def test_settings_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins=["*"])


def test_settings_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="too-short")


def test_settings_rejects_default_secret_or_debug_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret_key="dev-only-change-before-deploy-minimum-32-chars",
        )
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            debug=True,
            jwt_secret_key="explicit-non-default-prod-secret-key-32-plus-chars",
        )


def test_argon2id_password_hashing_and_verification(test_settings: Settings) -> None:
    hashed = hash_password("CorrectHorseBatteryStaple!9", settings=test_settings)
    assert hashed.startswith("$argon2id$")
    assert verify_password("CorrectHorseBatteryStaple!9", hashed, settings=test_settings) is True
    assert verify_password("WrongPassword", hashed, settings=test_settings) is False

    with pytest.raises(ValueError):
        hash_password("", settings=test_settings)


def test_jwt_issue_and_verify_roundtrip(test_settings: Settings) -> None:
    token = create_access_token(
        subject="user-123",
        role="student",
        tenant_id="tenant-abc",
        extra_claims={"locale": "en-IN"},
        settings=test_settings,
    )
    claims = decode_access_token(token, settings=test_settings)
    assert claims["sub"] == "user-123"
    assert claims["role"] == "student"
    assert claims["tenant_id"] == "tenant-abc"
    assert claims["locale"] == "en-IN"
    assert claims["type"] == "access"


def test_jwt_rejects_tampered_secret(test_settings: Settings) -> None:
    token = create_access_token(subject="u1", role="teacher", settings=test_settings)
    other = Settings(
        app_env="test",
        jwt_secret_key="different-secret-key-that-is-over-32-characters-long",
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, settings=other)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("=SUM(A1:A2)", "'=SUM(A1:A2)"),
        ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
        ("-2+3", "'-2+3"),
        ("@SUM(1,2)", "'@SUM(1,2)"),
        ("\tHYPERLINK()", "'\tHYPERLINK()"),
        ("\r=1+1", "'\r=1+1"),
        ("Linear Equations in Two Variables", "Linear Equations in Two Variables"),
        ("", ""),
    ],
)
def test_spreadsheet_formula_neutralization(raw: str, expected: str) -> None:
    assert sanitize_spreadsheet_cell(raw) == expected
