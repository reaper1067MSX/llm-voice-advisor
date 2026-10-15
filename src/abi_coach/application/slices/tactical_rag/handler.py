"""Tactical RAG Vertical Slice (Application Layer)."""

from dataclasses import dataclass
from typing import Any, Dict, List

from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result
from abi_coach.domain.entities.tactical_fact import TacticalDiff, TacticalFact
from abi_coach.domain.ports.knowledge_port import KnowledgeRepositoryPort


@dataclass(frozen=True)
class SearchKnowledgeQuery:
    query: str
    game: str = "generic"
    limit: int = 5


@dataclass(frozen=True)
class ReconcileFactCommand:
    entity_key: str
    observed_data: Dict[str, Any]
    game: str = "generic"
    reason: str = "vision_observed"


class TacticalRagHandler:
    """Use Case Handler for tactical fact search and self-healing reconciliation."""

    def __init__(self, knowledge_port: KnowledgeRepositoryPort):
        self.knowledge_port = knowledge_port

    def handle_search(self, query: SearchKnowledgeQuery) -> Result[List[TacticalFact], DomainError]:
        return self.knowledge_port.search(query=query.query, game=query.game, limit=query.limit)

    def handle_reconcile(self, command: ReconcileFactCommand) -> Result[List[TacticalDiff], DomainError]:
        return self.knowledge_port.reconcile(
            entity_key=command.entity_key,
            observed_data=command.observed_data,
            game=command.game,
            reason=command.reason,
        )
