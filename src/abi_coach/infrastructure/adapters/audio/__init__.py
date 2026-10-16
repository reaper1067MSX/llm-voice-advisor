"""Audio Adapters package."""

from abi_coach.infrastructure.adapters.audio.faster_whisper_adapter import (
    EdgeTtsAudioOutputAdapter,
    FasterWhisperAudioInputAdapter,
)
from abi_coach.infrastructure.adapters.audio.listener import AudioListener, ListenerConfig
from abi_coach.infrastructure.adapters.audio.speaker import Speaker, SpeakerConfig

__all__ = [
    "AudioListener",
    "Speaker",
    "ListenerConfig",
    "SpeakerConfig",
    "FasterWhisperAudioInputAdapter",
    "EdgeTtsAudioOutputAdapter",
]
