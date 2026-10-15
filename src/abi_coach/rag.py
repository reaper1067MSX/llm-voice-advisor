"""Backward compatibility shim for abi_coach.rag -> abi_coach.slices.tactical_rag.rag."""

from abi_coach.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG

__all__ = ["KnowledgeItem", "KnowledgeRAG"]
