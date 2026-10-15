"""Knowledge Repository Outbound Port (Domain Layer)."""

from typing import Any, Dict, List, Optional, Protocol
from abi_coach.domain.common.errors import StorageError
from abi_coach.domain.common.result import Result
from abi_coach.domain.entities.tactical_fact import TacticalDiff, TacticalFact


class KnowledgeRepositoryPort(Protocol):
    """Port for factual RAG indexing, BM25 searching, and knowledge reconciliation."""

    def search(
        self,
        query: str,
        game: str = "generic",
        limit: int = 5,
    ) -> Result[List[TacticalFact], StorageError]:
        """Search tactical facts using full-text indexing."""
        ...

    def get_by_key(
        self,
        entity_key: str,
        game: str = "generic",
    ) -> Result[Optional[TacticalFact], StorageError]:
        """Retrieve discrete fact by key."""
        ...

    def save(
        self,
        fact: TacticalFact,
    ) -> Result[None, StorageError]:
        """Upsert fact into persistent store."""
        ...

    def reconcile(
        self,
        entity_key: str,
        observed_data: Dict[str, Any],
        game: str = "generic",
        reason: str = "vision_observed",
    ) -> Result[List[TacticalDiff], StorageError]:
        """Detect discrepancy, update fact, and return diffs."""
        ...
