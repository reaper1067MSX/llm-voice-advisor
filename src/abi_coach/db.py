"""Backward compatibility shim for abi_coach.db."""

from abi_coach.core.storage.db import DatabaseManager

__all__ = ["DatabaseManager"]
