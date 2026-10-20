"""Audio Adapters package."""

from abi_coach.infrastructure.adapters.audio.faster_whisper_adapter import (
    EdgeTtsAudioOutputAdapter,
    FasterWhisperAudioInputAdapter,
)
from abi_coach.infrastructure.adapters.audio.listener import AudioListener, ListenerConfig
from abi_coach.infrastructure.adapters.audio.silero_vad_detector import SileroVadDetector
from abi_coach.infrastructure.adapters.audio.speaker import Speaker, SpeakerConfig
from abi_coach.infrastructure.adapters.audio.whisper_transcriber import WhisperTranscriber

__all__ = [
    "AudioListener",
    "SileroVadDetector",
    "WhisperTranscriber",
    "Speaker",
    "ListenerConfig",
    "SpeakerConfig",
    "FasterWhisperAudioInputAdapter",
    "EdgeTtsAudioOutputAdapter",
]
