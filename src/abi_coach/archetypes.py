"""Backward compatibility shim for abi_coach.archetypes."""

from abi_coach.slices.archetypes.manager import (
    ArchetypeDefinition,
    ArchetypeManager,
    DynamicEntity,
    EngramObservation,
    TopicContext,
)

__all__ = [
    "ArchetypeDefinition",
    "ArchetypeManager",
    "DynamicEntity",
    "EngramObservation",
    "TopicContext",
]
