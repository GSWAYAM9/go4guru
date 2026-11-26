"""Go4Guru async worker runtime bootstrap (Phase 0)."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import UTC, datetime

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import Redis

logger = logging.getLogger("go4guru.worker")


class WorkerSettings(BaseSettings):
    """Environment configuration for background workers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="go4guru-worker")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0")
    redis_connect_timeout_seconds: float = Field(default=2.0, gt=0.0, le=30.0)
    poll_interval_seconds: float = Field(default=5.0, ge=0.5, le=60.0)


def configure_worker_logging(level: str = "INFO") -> None:
    """Emit structured single-line JSON logs for the worker runtime."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            json.dumps(
                {
                    "timestamp": "%(asctime)s",
                    "level": "%(levelname)s",
                    "logger": "%(name)s",
                    "message": "%(message)s",
                }
            )
        )
    )
    root.addHandler(handler)


async def check_worker_redis_readiness(settings: WorkerSettings) -> bool:
    """Verify Redis connectivity cleanly before polling outbox/queues."""
    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.redis_connect_timeout_seconds,
        socket_timeout=settings.redis_connect_timeout_seconds,
        decode_responses=True,
    )
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


async def run_once(settings: WorkerSettings | None = None) -> dict[str, object]:
    """Execute one deterministic worker readiness probe without blocking."""
    cfg = settings or WorkerSettings()
    configure_worker_logging(cfg.log_level)
    redis_ok = await check_worker_redis_readiness(cfg)
    status = "ready" if redis_ok else "degraded_redis_unavailable"
    logger.info("Worker readiness check finished: status=%s", status)
    return {
        "service": cfg.app_name,
        "environment": cfg.app_env,
        "status": status,
        "redis_connected": redis_ok,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    """CLI entrypoint for single readiness cycle verification."""
    result = asyncio.run(run_once())
    print(json.dumps(result))


if __name__ == "__main__":
    main()
