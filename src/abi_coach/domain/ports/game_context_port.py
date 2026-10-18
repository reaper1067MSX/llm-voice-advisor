"""Port alias for GameContextPort and AdvisorContextPort."""

from abi_coach.domain.ports.context_port import AdvisorContextPort

GameContextPort = AdvisorContextPort

__all__ = ["AdvisorContextPort", "GameContextPort"]
