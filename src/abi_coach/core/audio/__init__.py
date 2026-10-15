"""Audio hardware subsystem: AudioListener (VAD/Whisper) and Speaker (TTS)."""

from abi_coach.core.audio.listener import AudioListener, ListenerConfig, play_beep
from abi_coach.core.audio.speaker import Speaker

__all__ = ["AudioListener", "ListenerConfig", "Speaker", "play_beep"]
