"""Public contract boundary for classroom & multilingual module (Phase 4 + Phase 10)."""

from __future__ import annotations

from src.modules.classroom.multilingual_router import (
    languages_router,
    voice_multilingual_router,
)
from src.modules.classroom.router import (
    classroom_router,
    classroom_ws_router,
    voice_router,
    whiteboard_router,
)

MODULE_NAME = "classroom"
MODULE_PHASE = "Phase 4 + Phase 10 (Multilingual Expansion)"
MODULE_STATUS = "IMPLEMENTED"

__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "classroom_router",
    "classroom_ws_router",
    "languages_router",
    "voice_multilingual_router",
    "voice_router",
    "whiteboard_router",
]
