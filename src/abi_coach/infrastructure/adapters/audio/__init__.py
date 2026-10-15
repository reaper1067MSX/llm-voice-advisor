"""Audio Adapters package."""

from abi_coach.infrastructure.adapters.audio.faster_whisper_adapter import (
    EdgeTtsAudioOutputAdapter,
    FasterWhisperAudioInputAdapter,
)

__all__ = [
    "FasterWhisperAudioInputAdapter",
    "EdgeTtsAudioOutputAdapter",
]
