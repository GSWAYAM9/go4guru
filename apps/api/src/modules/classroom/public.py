"""Public contract boundary for classroom module (Phase 4 Live Classroom, Whiteboard & Voice)."""

from __future__ import annotations

from src.modules.classroom.router import (
    classroom_router,
    classroom_ws_router,
    languages_router,
    voice_router,
    whiteboard_router,
)

MODULE_NAME = "classroom"
MODULE_PHASE = "Phase 4"
MODULE_STATUS = "IMPLEMENTED"

__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "classroom_router",
    "classroom_ws_router",
    "languages_router",
    "voice_router",
    "whiteboard_router",
]
