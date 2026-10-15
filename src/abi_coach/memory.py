"""Backward compatibility shim for abi_coach.memory -> abi_coach.slices.companion_memory.memory."""

from abi_coach.slices.companion_memory.memory import CompanionMemory, MemoryItem

__all__ = ["CompanionMemory", "MemoryItem"]
