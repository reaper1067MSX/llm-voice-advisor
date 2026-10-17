"""Port defining autonomous domain/game context capabilities."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class AdvisorContextPort(Protocol):
    """Port representing an autonomous game/domain context containing its own knowledge and resolution rules."""

    @property
    def context_id(self) -> str:
        """Canonical identifier for the context."""
        ...

    def try_resolve_fast_path(self, prompt: str) -> Optional[str]:
        """Attempt immediate deterministic resolution using context's own knowledge."""
        ...

    def get_rag_context(self, prompt: str, limit: int = 2) -> Optional[str]:
        """Retrieve formatted RAG context for this domain."""
        ...

    def get_prompt_preset(self) -> str:
        """Get the base system instruction template for this context."""
        ...
