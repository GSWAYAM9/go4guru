"""Public contract boundary for analytics module (`F-034`)."""

from __future__ import annotations

from src.modules.analytics.router import analytics_router
from src.modules.analytics.service import process_outbox_learning_events

MODULE_NAME = "analytics"
MODULE_PHASE = "Phase 2"
MODULE_STATUS = "IMPLEMENTED"

__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "analytics_router",
    "process_outbox_learning_events",
]
