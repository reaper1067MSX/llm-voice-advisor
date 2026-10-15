"""Tactical RAG slice: fast BM25 retrieval, knowledge seeding, and self-healing reconciler."""

from abi_coach.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG
from abi_coach.slices.tactical_rag.reconciler import KnowledgeReconciler, ReconciliationDiff

__all__ = [
    "KnowledgeItem",
    "KnowledgeRAG",
    "ReconciliationDiff",
    "KnowledgeReconciler",
]
