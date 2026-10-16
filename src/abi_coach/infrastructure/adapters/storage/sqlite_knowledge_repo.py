"""SQLite Knowledge Repository implementing KnowledgeRepositoryPort."""

import json
from typing import Any, Dict, List, Optional

from abi_coach.domain.common.errors import StorageError
from abi_coach.domain.common.result import Result, fail, ok
from abi_coach.domain.common.value_objects import ConfidenceScore
from abi_coach.domain.entities.tactical_fact import TacticalDiff, TacticalFact
from abi_coach.domain.ports.knowledge_port import KnowledgeRepositoryPort
from abi_coach.application.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG
from abi_coach.application.slices.tactical_rag.reconciler import KnowledgeReconciler


class SqliteKnowledgeRepository(KnowledgeRepositoryPort):
    """Hexagonal Adapter providing factual retrieval and reconciliation over SQLite FTS5."""

    def __init__(self, rag: KnowledgeRAG, reconciler: KnowledgeReconciler):
        self.rag = rag
        self.reconciler = reconciler

    def search(
        self,
        query: str,
        game: str = "generic",
        limit: int = 5,
    ) -> Result[List[TacticalFact], StorageError]:
        try:
            raw_items = self.rag.search(query=query, game=game, limit=limit)
            facts: List[TacticalFact] = []
            for item in raw_items:
                data = {}
                try:
                    data = json.loads(item.get("data_json", "{}"))
                except Exception:
                    pass

                facts.append(
                    TacticalFact(
                        game=item.get("game", game),
                        category=item.get("category", "general"),
                        entity_key=item.get("entity_key", ""),
                        title=item.get("title", ""),
                        data_payload=data,
                        summary=item.get("summary", ""),
                        source=item.get("source", "db"),
                        confidence=ConfidenceScore(float(item.get("confidence", 1.0))),
                        game_version=item.get("game_version", "1.0"),
                    )
                )
            return ok(facts)
        except Exception as e:
            return fail(
                StorageError(
                    code="KNOWLEDGE_SEARCH_ERROR",
                    message=f"Error al buscar en base de conocimiento: {e}",
                    operation="search",
                )
            )

    def get_by_key(
        self,
        entity_key: str,
        game: str = "generic",
    ) -> Result[Optional[TacticalFact], StorageError]:
        try:
            item = self.rag.get_entity(entity_key=entity_key)
            if not item:
                return ok(None)

            data = {}
            try:
                data = json.loads(item.get("data_json", "{}"))
            except Exception:
                pass

            fact = TacticalFact(
                game=item.get("game", game),
                category=item.get("category", "general"),
                entity_key=item.get("entity_key", entity_key),
                title=item.get("title", ""),
                data_payload=data,
                summary=item.get("summary", ""),
                source=item.get("source", "db"),
                confidence=ConfidenceScore(float(item.get("confidence", 1.0))),
                game_version=item.get("game_version", "1.0"),
            )
            return ok(fact)
        except Exception as e:
            return fail(
                StorageError(
                    code="KNOWLEDGE_GET_ERROR",
                    message=f"Error al obtener entidad {entity_key}: {e}",
                    operation="get_by_key",
                )
            )

    def save(
        self,
        fact: TacticalFact,
    ) -> Result[None, StorageError]:
        try:
            k_item = KnowledgeItem(
                game=fact.game,
                category=fact.category,
                entity_key=fact.entity_key,
                title=fact.title,
                data_json=json.dumps(fact.data_payload, ensure_ascii=False),
                summary=fact.summary,
                source=fact.source,
                game_version=fact.game_version,
                confidence=fact.confidence.score,
            )
            self.rag.upsert_knowledge(k_item)
            return ok(None)
        except Exception as e:
            return fail(
                StorageError(
                    code="KNOWLEDGE_SAVE_ERROR",
                    message=f"Error al guardar hecho táctico {fact.entity_key}: {e}",
                    operation="save",
                )
            )

    def reconcile(
        self,
        entity_key: str,
        observed_data: Dict[str, Any],
        game: str = "generic",
        reason: str = "vision_observed",
    ) -> Result[List[TacticalDiff], StorageError]:
        try:
            diffs = self.reconciler.reconcile_entity(
                entity_key=entity_key,
                observed_data=observed_data,
                game=game,
                reason=reason,
            )
            domain_diffs = [
                TacticalDiff(
                    entity_key=d.entity_key,
                    field_name=d.field_name,
                    old_value=d.old_value,
                    new_value=d.new_value,
                    reason=d.reason,
                )
                for d in diffs
            ]
            return ok(domain_diffs)
        except Exception as e:
            return fail(
                StorageError(
                    code="KNOWLEDGE_RECONCILE_ERROR",
                    message=f"Error al reconciliar {entity_key}: {e}",
                    operation="reconcile",
                )
            )
