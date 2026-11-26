"""Phase 0 tests for async worker bootstrap and truthful Redis readiness."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

WORKER_SRC = str(Path(__file__).resolve().parents[1] / "src")
if WORKER_SRC not in sys.path:
    sys.path.insert(0, WORKER_SRC)

import go4guru_worker.main as worker_mod  # noqa: E402


def test_worker_reports_degraded_when_redis_unreachable() -> None:
    """Worker must never fake readiness when Redis connection fails."""
    settings = worker_mod.WorkerSettings(
        redis_url="redis://127.0.0.1:6399/0",
        redis_connect_timeout_seconds=0.2,
    )

    with patch.object(
        worker_mod,
        "check_worker_redis_readiness",
        new=AsyncMock(return_value=False),
    ):
        result = asyncio.run(worker_mod.run_once(settings))

    assert result["status"] == "degraded_redis_unavailable"
    assert result["redis_connected"] is False


def test_worker_reports_ready_when_redis_pings() -> None:
    """Worker reports ready when Redis PING succeeds."""
    settings = worker_mod.WorkerSettings()

    with patch.object(
        worker_mod,
        "check_worker_redis_readiness",
        new=AsyncMock(return_value=True),
    ):
        result = asyncio.run(worker_mod.run_once(settings))

    assert result["status"] == "ready"
    assert result["redis_connected"] is True
