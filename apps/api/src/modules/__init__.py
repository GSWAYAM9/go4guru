"""Modular monolith domain boundary registry (docs/ARCHITECTURE.md)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainModuleDescriptor:
    """Metadata describing a domain module's rollout state."""

    name: str
    status: str
    planned_phase: str


DOMAIN_MODULES: tuple[DomainModuleDescriptor, ...] = (
    DomainModuleDescriptor(name="identity", status="implemented", planned_phase="Phase 1/7"),
    DomainModuleDescriptor(name="organization", status="implemented", planned_phase="Phase 8"),
    DomainModuleDescriptor(name="curriculum", status="implemented", planned_phase="Phase 1"),
    DomainModuleDescriptor(name="content", status="partial_phase_1", planned_phase="Phase 1"),
    DomainModuleDescriptor(name="question_bank", status="implemented", planned_phase="Phase 1"),
    DomainModuleDescriptor(name="assessment", status="implemented", planned_phase="Phase 1/2"),
    DomainModuleDescriptor(name="learning", status="implemented", planned_phase="Phase 1/5"),
    DomainModuleDescriptor(name="revision", status="implemented", planned_phase="Phase 5"),
    DomainModuleDescriptor(name="ai", status="implemented", planned_phase="Phase 3"),
    DomainModuleDescriptor(name="classroom", status="implemented", planned_phase="Phase 4"),
    DomainModuleDescriptor(name="homework", status="implemented", planned_phase="Phase 6"),
    DomainModuleDescriptor(name="teacher", status="implemented", planned_phase="Phase 7"),
    DomainModuleDescriptor(name="mentor", status="implemented", planned_phase="Phase 7"),
    DomainModuleDescriptor(name="billing", status="implemented", planned_phase="Phase 8"),
    DomainModuleDescriptor(name="analytics", status="implemented", planned_phase="Phase 2"),
    DomainModuleDescriptor(name="notifications", status="implemented", planned_phase="Phase 5"),
)
