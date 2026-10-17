"""Domain Outbound Ports package (Hexagonal Architecture)."""

from abi_coach.domain.ports.audio_port import AudioInputPort, AudioOutputPort
from abi_coach.domain.ports.blackboard_port import BlackboardPort
from abi_coach.domain.ports.knowledge_port import KnowledgeRepositoryPort
from abi_coach.domain.ports.llm_port import LLMProviderPort, LLMResponseDTO
from abi_coach.domain.ports.memory_port import MemoryRepositoryPort
from abi_coach.domain.ports.vision_port import ReportDisplayPort, ScreenCapturePort, ScreenCaptureResultDTO

from abi_coach.domain.ports.context_port import AdvisorContextPort
from abi_coach.domain.ports.game_context_port import GameContextPort
from abi_coach.domain.ports.history_port import ConversationHistoryPort

__all__ = [
    "LLMProviderPort",
    "LLMResponseDTO",
    "KnowledgeRepositoryPort",
    "MemoryRepositoryPort",
    "AudioInputPort",
    "AudioOutputPort",
    "ScreenCapturePort",
    "ScreenCaptureResultDTO",
    "ReportDisplayPort",
    "BlackboardPort",
    "ConversationHistoryPort",
    "AdvisorContextPort",
    "GameContextPort",
]

