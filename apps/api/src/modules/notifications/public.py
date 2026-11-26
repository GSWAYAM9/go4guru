"""Public contract boundary for notifications module (`F-035` in-app alerts)."""

from __future__ import annotations

from src.modules.notifications.router import notifications_router
from src.modules.notifications.service import emit_in_app_notification

MODULE_NAME = "notifications"
MODULE_PHASE = "Phase 5"
MODULE_STATUS = "IMPLEMENTED_IN_APP"

__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "emit_in_app_notification",
    "notifications_router",
]
