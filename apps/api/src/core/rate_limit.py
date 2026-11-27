"""Distributed Redis-backed rate limiting with safe in-memory fallback for auth endpoints."""

from __future__ import annotations

import logging
from fastapi import Request, status

from src.core.config import Settings, get_settings
from src.core.errors import AppError
from src.core.hardening import FixedWindowRateLimiter, RateLimitDecision

logger = logging.getLogger("go4guru.security.rate_limit")

_FALLBACK_LIMITER = FixedWindowRateLimiter(max_buckets=20_000)


def extract_client_ip(request: Request) -> str:
    """Resolve client IP from connection metadata (without blindly trusting spoofed headers)."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def evaluate_rate_limit(
    request: Request,
    *,
    scope: str,
    subject: str | None = None,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> RateLimitDecision:
    """Check rate limit via Redis INCR/EXPIRE when reachable, else local FixedWindowRateLimiter."""
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    effective_limit = limit if limit is not None else settings.auth_rate_limit_max_attempts
    effective_window = (
        window_seconds if window_seconds is not None else settings.auth_rate_limit_window_seconds
    )

    client_ip = extract_client_ip(request)
    normalized_subject = (subject or "").strip().lower()
    bucket_key = f"rl:{scope}:{client_ip}:{normalized_subject}" if normalized_subject else f"rl:{scope}:{client_ip}"

    redis_mgr = getattr(request.app.state, "redis", None)
    if redis_mgr is not None and getattr(redis_mgr, "client", None) is not None:
        try:
            redis_client = redis_mgr.client
            count = int(await redis_client.incr(bucket_key))
            if count == 1:
                await redis_client.expire(bucket_key, effective_window)
                ttl = effective_window
            else:
                ttl_raw = await redis_client.ttl(bucket_key)
                ttl = int(ttl_raw) if isinstance(ttl_raw, int) and ttl_raw > 0 else effective_window
            allowed = count <= effective_limit
            return RateLimitDecision(
                allowed=allowed,
                remaining=max(0, effective_limit - count),
                retry_after_seconds=0 if allowed else max(1, ttl),
                current_count=count,
                limit=effective_limit,
            )
        except Exception:
            logger.debug(
                "Redis unavailable for rate limiting; using in-process fallback.",
                extra={"event": "rate_limit_redis_fallback", "scope": scope},
            )

    return _FALLBACK_LIMITER.check(
        bucket_key,
        limit=effective_limit,
        window_seconds=effective_window,
    )


async def enforce_auth_rate_limit(
    request: Request,
    *,
    scope: str,
    subject: str | None = None,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> None:
    """Enforce brute-force throttling on authentication endpoints, raising HTTP 429 on breach."""
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    if settings.app_env == "test" and limit is None:
        # Keep integration suites deterministic unless a test passes an explicit limit.
        return

    decision = await evaluate_rate_limit(
        request,
        scope=scope,
        subject=subject,
        limit=limit,
        window_seconds=window_seconds,
    )
    if not decision.allowed:
        raise AppError(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMITED",
            message="Too many authentication attempts. Please wait and try again.",
            details={
                "scope": scope,
                "retry_after_seconds": decision.retry_after_seconds,
            },
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
