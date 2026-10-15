"""Backward compatibility shim for abi_coach.reconciler -> abi_coach.slices.tactical_rag.reconciler."""

from abi_coach.slices.tactical_rag.reconciler import KnowledgeReconciler, ReconciliationDiff

__all__ = ["KnowledgeReconciler", "ReconciliationDiff"]
