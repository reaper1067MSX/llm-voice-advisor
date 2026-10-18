"""Functional behavioral unit tests for AdvisorOrchestrator."""

from pathlib import Path

from abi_coach.application.orchestration.advisor_orchestrator import AdvisorOrchestrator
from abi_coach.application.services.context_factual_resolver import ContextFactualResolver
from abi_coach.application.services.history_manager import ConversationHistoryManager
from abi_coach.application.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG
from abi_coach.domain.entities.interaction_records import InteractionRequest
from abi_coach.infrastructure.adapters.llm.base import ProviderResponse
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.config.settings import AppConfig


class MockLLMProvider:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, system_instruction, **kwargs):
        self.calls.append({"prompt": prompt, "instruction": system_instruction})
        return ProviderResponse(
            spoken_text="Mock advice: Avanza con squadmate.",
            input_tokens=25,
            output_tokens=10,
            latency_ms=40.0,
        )


def test_deterministic_fast_path_factual_resolution(tmp_path: Path):
    """Verify factual queries resolve deterministically (sub-2ms, 0 tokens) without LLM."""
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


def test_multimodal_generative_llm_resolution():
    """Verify strategic/complex queries route through the generative LLM pipeline."""
    prov = MockLLMProvider()
    orchestrator = AdvisorOrchestrator(provider=prov)

    req = InteractionRequest(prompt="¿Cuál es la estrategia recomendada para esta zona?")
    result = orchestrator.execute(req)

    assert result.spoken_text == "Mock advice: Avanza con squadmate."
    assert len(prov.calls) == 1
    assert result.input_tokens == 25


def test_verbal_context_switch_and_state_transition(tmp_path: Path):
    """Verify verbal context switch intent is detected and executed without LLM latency."""
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False
    prov = MockLLMProvider()

    orchestrator = AdvisorOrchestrator(config=cfg, provider=prov)
    assert orchestrator.active_context_id == "generic"

    # Verbal context switch
    result = orchestrator.execute(InteractionRequest(prompt="¡Vamos a jugar Once Human!"))
    assert "Once Human" in result.spoken_text
    assert orchestrator.active_context_id == "once_human"
    assert len(prov.calls) == 0  # Handled without LLM latency


def test_voice_command_silence_interception():
    """Verify radio silence command is intercepted instantly by tactical FSM."""
    prov = MockLLMProvider()
    orchestrator = AdvisorOrchestrator(provider=prov)

    result = orchestrator.execute(InteractionRequest(prompt="Silencio de radio"))
    assert "silencio" in result.spoken_text.lower()
    assert orchestrator.fsm.state.value == "silence"
    assert len(prov.calls) == 0
