"""Audio Adapters implementing AudioInputPort and AudioOutputPort."""

from typing import Callable, Optional
from abi_coach.infrastructure.adapters.audio.listener import AudioListener
from abi_coach.infrastructure.adapters.audio.speaker import Speaker
from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result, fail, ok
from abi_coach.domain.ports.audio_port import AudioInputPort, AudioOutputPort


class FasterWhisperAudioInputAdapter(AudioInputPort):
    """Hexagonal Adapter wrapping AudioListener (VAD & faster-whisper GPU)."""

    def __init__(self, listener: AudioListener):
        self.listener = listener

    def start_listening(self) -> None:
        self.listener.start_stream()

    def pause_listening(self) -> None:
        self.listener.pause_listening()

    def resume_listening(self) -> None:
        self.listener.resume_listening()

    def listen_loop(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[str], None],
    ) -> None:
        self.listener.listen_ptt_loop(on_press, on_release)

    def close(self) -> None:
        self.listener.stop_ptt_loop()
        self.listener.close()


class EdgeTtsAudioOutputAdapter(AudioOutputPort):
    """Hexagonal Adapter wrapping Speaker (edge-tts / SAPI fallback)."""

    def __init__(self, speaker: Speaker):
        self.speaker = speaker

    def speak(self, text: str) -> Result[None, DomainError]:
        try:
            self.speaker.speak(text)
            return ok(None)
        except Exception as e:
            return fail(
                DomainError(
                    code="TTS_PLAYBACK_ERROR",
                    message=f"Error al reproducir audio por voz: {e}",
                    spoken_fallback="Error en la reproducción de voz.",
                )
            )

    def stop(self) -> None:
        self.speaker.stop()
