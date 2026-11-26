"""Redis async client wrapper and readiness check."""

from __future__ import annotations

from redis.asyncio import Redis

from src.core.config import Settings, get_settings


class RedisManager:
    """Lifecycle wrapper for async Redis connectivity."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client: Redis = Redis.from_url(
            self.settings.redis_url,
            socket_connect_timeout=self.settings.redis_connect_timeout_seconds,
            socket_timeout=self.settings.redis_connect_timeout_seconds,
            decode_responses=True,
        )

    async def check_connectivity(self) -> tuple[bool, str | None]:
        """Verify Redis connectivity with PING; never mask connection failures."""
        try:
            ok = bool(await self.client.ping())
            return ok, None if ok else "PingReturnedFalse"
        except Exception as exc:
            return False, exc.__class__.__name__

    async def close(self) -> None:
        """Close the Redis connection pool on shutdown."""
        await self.client.aclose()
