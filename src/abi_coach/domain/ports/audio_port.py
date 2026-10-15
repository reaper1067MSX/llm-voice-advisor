"""Audio Input and Output Outbound Ports (Domain Layer)."""

from typing import Callable, Optional, Protocol
from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result


class AudioInputPort(Protocol):
    """Port for microphone streaming, VAD, and local speech-to-text transcription."""

    def start_listening(self) -> None:
        ...

    def pause_listening(self) -> None:
        ...

    def resume_listening(self) -> None:
        ...

    def listen_loop(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[str], None],
    ) -> None:
        ...

    def close(self) -> None:
        ...


class AudioOutputPort(Protocol):
    """Port for speech synthesis and playback in headphones."""

    def speak(self, text: str) -> Result[None, DomainError]:
        ...

    def stop(self) -> None:
        ...
