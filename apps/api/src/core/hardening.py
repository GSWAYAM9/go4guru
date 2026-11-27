"""Pure-stdlib production hardening primitives (config invariants, origin checks, rate limits, headers).

Kept intentionally free of FastAPI/Pydantic/SQLAlchemy imports so security invariants can be
exhaustively verified by pure-stdlib unit tests in any Python 3 environment.
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlparse

PLATFORM_PHASE = "phase_11_production_readiness"

_SAFE_AUDIO_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.mp3$")
_LOCALHOST_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})


def normalize_origin(origin: str) -> str:
    """Normalize an HTTP Origin string by stripping whitespace and trailing slashes."""
    return origin.strip().rstrip("/").lower()


def is_origin_allowed(origin: str | None, allowed_origins: Sequence[str]) -> bool:
    """Return True iff the provided Origin matches an explicit configured allowlist entry."""
    if not origin or not origin.strip():
        return False
    normalized = normalize_origin(origin)
    allowed_set = {
        normalize_origin(entry)
        for entry in allowed_origins
        if entry and entry.strip() and entry.strip() != "*"
    }
    return normalized in allowed_set


def is_safe_audio_cache_filename(filename: str) -> bool:
    """Validate that a cached voice audio filename is a flat .mp3 filename with no traversal."""
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return False
    return bool(_SAFE_AUDIO_FILENAME_RE.match(filename))


def validate_production_config_invariants(
    *,
    app_env: str,
    debug: bool,
    jwt_secret: str,
    database_url: str,
    cookie_secure: bool,
    cors_allowed_origins: Sequence[str],
    trusted_hosts: Sequence[str],
) -> list[str]:
    """Return a list of configuration security violations for the given runtime environment."""
    violations: list[str] = []
    if len(jwt_secret) < 32:
        violations.append("jwt_secret_key must be at least 32 characters.")

    if any(entry.strip() == "*" for entry in cors_allowed_origins):
        violations.append("Wildcard '*' is forbidden in cors_allowed_origins.")

    if app_env in {"staging", "production"}:
        if jwt_secret.startswith("dev-only") or "CHANGE_ME" in jwt_secret:
            violations.append(
                "Staging/production requires an explicit non-default JWT_SECRET_KEY."
            )
        if debug:
            violations.append("DEBUG=true is forbidden in staging and production.")
        if "postgres:postgres@127.0.0.1" in database_url or "postgres:postgres@localhost" in database_url:
            violations.append(
                "Staging/production must not use default local postgres:postgres database credentials."
            )
        non_empty_hosts = [h.strip() for h in trusted_hosts if h and h.strip()]
        if not non_empty_hosts or "*" in non_empty_hosts:
            violations.append(
                "Staging/production requires explicit non-wildcard trusted_hosts."
            )

    if app_env == "production":
        if not cookie_secure:
            violations.append("COOKIE_SECURE=true is required in production.")
        if not cors_allowed_origins:
            violations.append("Production requires at least one explicit HTTPS CORS origin.")
        else:
            for origin in cors_allowed_origins:
                parsed = urlparse(origin.strip())
                host = (parsed.hostname or "").lower()
                if parsed.scheme != "https":
                    violations.append(
                        f"Production CORS origin must use https:// (got '{origin}')."
                    )
                if host in _LOCALHOST_HOSTS:
                    violations.append(
                        f"Production CORS origin must not target localhost (got '{origin}')."
                    )

    return violations


def build_api_security_headers(app_env: str) -> dict[str, str]:
    """Build baseline HTTP security response headers for API responses."""
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    }
    if app_env in {"staging", "production"}:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


@dataclass(frozen=True)
class RateLimitDecision:
    """Outcome of evaluating a single rate-limit bucket."""

    allowed: bool
    remaining: int
    retry_after_seconds: int
    current_count: int
    limit: int


class FixedWindowRateLimiter:
    """Bounded in-memory fixed-window rate limiter used for unit tests and Redis fallback."""

    def __init__(self, max_buckets: int = 10_000) -> None:
        self._max_buckets = max(16, max_buckets)
        self._buckets: dict[str, tuple[int, float]] = {}

    def _prune(self, now: float) -> None:
        if len(self._buckets) < self._max_buckets:
            return
        expired = [k for k, (_, reset_at) in self._buckets.items() if reset_at <= now]
        for key in expired:
            self._buckets.pop(key, None)
        if len(self._buckets) >= self._max_buckets:
            # Drop oldest entries if still saturated
            oldest = sorted(self._buckets.items(), key=lambda kv: kv[1][1])
            for key, _ in oldest[: max(1, len(self._buckets) // 4)]:
                self._buckets.pop(key, None)

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        """Consume one request unit for `key` and return allow/deny with Retry-After."""
        ts = time.monotonic() if now is None else now
        self._prune(ts)
        entry = self._buckets.get(key)
        if entry is None or entry[1] <= ts:
            count = 1
            reset_at = ts + float(window_seconds)
        else:
            count = entry[0] + 1
            reset_at = entry[1]
        self._buckets[key] = (count, reset_at)

        retry_after = max(1, int(math.ceil(reset_at - ts)))
        allowed = count <= limit
        remaining = max(0, limit - count)
        return RateLimitDecision(
            allowed=allowed,
            remaining=remaining,
            retry_after_seconds=0 if allowed else retry_after,
            current_count=count,
            limit=limit,
        )

    def reset(self) -> None:
        """Clear all tracked buckets (used in test fixtures)."""
        self._buckets.clear()
