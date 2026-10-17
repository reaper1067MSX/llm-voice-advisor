"""Unit tests for AdvisorOrchestrator unified query and process execution."""

from pathlib import Path
from abi_coach.application.orchestration.advisor_orchestrator import AdvisorOrchestrator
from abi_coach.application.services.context_factual_resolver import ContextFactualResolver
from abi_coach.application.services.history_manager import ConversationHistoryManager
from abi_coach.application.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG
from abi_coach.domain.entities.interaction_records import InteractionRequest
from abi_coach.infrastructure.adapters.llm.base import ProviderResponse
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager


class MockLLMProvider:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, system_instruction, **kwargs):
        self.calls.append({"prompt": prompt, "instruction": system_instruction})
        return ProviderResponse(
            spoken_text="Mock advice: Avanza con cautela.",
            input_tokens=25,
            output_tokens=10,
            latency_ms=45.0,
        )


def test_advisor_orchestrator_deterministic_fast_path(tmp_path: Path):
    """Verify deterministic factual queries resolve instantly (0 tokens) via fast path."""
    db = DatabaseManager(str(tmp_path / "fast_path.db"))
    rag = KnowledgeRAG(db, default_game="abi")
    rag.upsert_knowledge(
        KnowledgeItem(
            game="abi",
            category="ammo",
            entity_key="ammo:m80",
            title="Bala M80 7.62x51",
            summary="Munición militar estándar",
            data_json='{"penetration": 44, "damage": 76, "tier": 4}',
        )
    )
    prov = MockLLMProvider()
    resolver = ContextFactualResolver(rag=rag)
    history = ConversationHistoryManager(10)
    orchestrator = AdvisorOrchestrator(provider=prov, factual_resolver=resolver, history_mgr=history)

    req = InteractionRequest(prompt="¿Qué penetración tiene la bala M80?", context_id="abi")
    result = orchestrator.execute(req)

    assert "44 de penetración" in result.spoken_text
    assert "76 de daño base" in result.spoken_text
    assert result.input_tokens == 0
    assert len(prov.calls) == 0  # LLM was NOT invoked


def test_advisor_orchestrator_generative_llm_fallback():
    """Verify strategic/complex queries route through the generative LLM pipeline."""
    prov = MockLLMProvider()
    orchestrator = AdvisorOrchestrator(provider=prov)

    req = InteractionRequest(prompt="¿Cuál es la estrategia recomendada para esta zona?")
    result = orchestrator.execute(req)

    assert result.spoken_text == "Mock advice: Avanza con cautela."
    assert len(prov.calls) == 1
    assert result.input_tokens == 25
