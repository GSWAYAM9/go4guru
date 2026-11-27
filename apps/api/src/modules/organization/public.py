"""Public contract boundary for organization module (Phase 8 F-003)."""

from __future__ import annotations

from src.modules.organization.router import organization_router

MODULE_NAME = "organization"
MODULE_PHASE = "Phase 8"
MODULE_STATUS = "IMPLEMENTED"

__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "organization_router",
]
