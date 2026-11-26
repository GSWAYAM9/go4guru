"""Public contract boundary for revision module (Phase 5 Flashcards, SM-2+ & Planner)."""

from __future__ import annotations

from src.modules.revision.router import revision_router

MODULE_NAME = "revision"
MODULE_PHASE = "Phase 5"
MODULE_STATUS = "IMPLEMENTED"

__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "revision_router",
]
