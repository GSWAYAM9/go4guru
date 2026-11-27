"""Pure-stdlib guardian consent and parent privacy policy logic (F-004, F-033)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

DEFAULT_PARENT_PRIVACY_SETTINGS: dict[str, bool] = {
    "share_learning_summary": True,
    "share_weak_topics": True,
    "share_upcoming_tests": True,
    "allow_raw_ai_transcripts": False,
}


def generate_consent_verification_code() -> str:
    """Generate a human-enterable 8-character uppercase consent code."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


def hash_consent_verification_code(code: str, *, salt: str) -> str:
    """Hash a guardian consent code with SHA-256 keyed by link-specific salt."""
    normalized = code.strip().upper()
    return hashlib.sha256(f"{salt}:{normalized}".encode("utf-8")).hexdigest()


def verify_consent_verification_code(code: str, *, salt: str, expected_hash: str | None) -> bool:
    """Constant-time verification of a guardian consent code."""
    if not expected_hash or not code or not code.strip():
        return False
    candidate = hash_consent_verification_code(code, salt=salt)
    return hmac.compare_digest(candidate, expected_hash)


def sanitize_parent_privacy_settings(
    requested: dict[str, Any] | None,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, bool]:
    """Normalize parent privacy settings while hard-locking raw AI transcripts off.

    Child-safety invariant (AGENTS.md Section 8):
    Linked parents receive privacy-preserving learning summaries and MUST NEVER
    receive unrestricted access to raw student AI chat transcripts.
    """
    base: dict[str, bool] = dict(DEFAULT_PARENT_PRIVACY_SETTINGS)
    if existing:
        for key in ("share_learning_summary", "share_weak_topics", "share_upcoming_tests"):
            if key in existing:
                base[key] = bool(existing[key])
    if requested:
        for key in ("share_learning_summary", "share_weak_topics", "share_upcoming_tests"):
            if key in requested:
                base[key] = bool(requested[key])
    # Hard lock: raw AI transcripts are never exposed to parent accounts.
    base["allow_raw_ai_transcripts"] = False
    return base
