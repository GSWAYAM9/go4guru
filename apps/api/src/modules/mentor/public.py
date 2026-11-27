"""Public contract boundary for mentor module (Phase 7 F-032)."""

from __future__ import annotations

from src.modules.mentor.router import mentor_router

MODULE_NAME = "mentor"
MODULE_PHASE = "Phase 7"
MODULE_STATUS = "IMPLEMENTED"

__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "mentor_router",
]
