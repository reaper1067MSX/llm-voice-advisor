"""Audio input and speech-to-text listener coordinator for ABI Coach."""

import collections
import queue
import time
from collections.abc import Callable
from typing import Any, Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from abi_coach.infrastructure.adapters.audio.silero_vad_detector import SileroVadDetector
from abi_coach.infrastructure.adapters.audio.whisper_transcriber import (
    WhisperTranscriber,
    _setup_cuda_dlls,
)
from abi_coach.infrastructure.adapters.logging.structured_logger import log_event, log_exception
from abi_coach.infrastructure.adapters.platform.win32_audio_hotkey import (
    GlobalMuteHotkeyMonitor,
    play_beep,
)
from abi_coach.infrastructure.config.settings import ListenerConfig


class AudioListener:
    """High-performance audio listener coordinating stream, Silero VAD, and Whisper STT."""

    def __init__(
        self,
        config: ListenerConfig,
        vad_detector: Optional[SileroVadDetector] = None,
        transcriber: Optional[WhisperTranscriber] = None,
        hotkey_monitor: Optional[GlobalMuteHotkeyMonitor] = None,
    ) -> None:
        self.config = config
        self._running = False
        self._is_paused = False
        self._is_muted = False
        self._stream: Optional[sd.InputStream] = None
        self._vad_detector = vad_detector or SileroVadDetector()
        self._transcriber = transcriber or WhisperTranscriber(config)
        self._whisper: Optional[WhisperModel] = self._transcriber.model
        self._vad_model: Optional[Any] = self._vad_detector.vad_model
        mute_key = getattr(config, "mute_key", "f10")
        self._hotkey_monitor = hotkey_monitor or GlobalMuteHotkeyMonitor(mute_key=mute_key)
        self._audio_queue: queue.Queue[tuple[np.ndarray, float]] = queue.Queue(maxsize=300)
        self._pre_buffer: collections.deque[np.ndarray] = collections.deque(maxlen=10)
        self._test_chunks: list[np.ndarray] = []

    def init_whisper(self) -> WhisperModel:
        self._whisper = self._transcriber.init_model()
        return self._whisper

    def init_vad(self) -> Optional[Any]:
        self._vad_model = self._vad_detector.init_vad()
        return self._vad_model

    def get_speech_probability(self, chunk: np.ndarray) -> float:
        threshold = getattr(self.config, "vad_threshold", 0.02)
        return self._vad_detector.get_speech_probability(chunk, vad_threshold=threshold)

    def transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        result = self._transcriber.transcribe(audio_data)
        self._whisper = self._transcriber.model
        return result

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        chunk = indata.copy().flatten()
        try:
            self._audio_queue.put_nowait((chunk, float(np.sqrt(np.mean(chunk**2)))))
        except queue.Full:
            pass

    def _drain_audio_queue(self) -> list[np.ndarray]:
        drained: list[np.ndarray] = []
        while not self._audio_queue.empty():
            try:
                drained.append(self._audio_queue.get_nowait()[0])
            except queue.Empty:
                break
        return drained

    def start_stream(self) -> None:
        if self._stream is not None:
            return
        try:
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=1,
                blocksize=512,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
        except (sd.PortAudioError, OSError, RuntimeError, ValueError) as exc:
            log_exception("AudioWorker", "start_stream", exc)

    def record_seconds(self, duration_sec: float = 3.0) -> Optional[str]:
        self.start_stream()
        self._drain_audio_queue()
        recorded: list[np.ndarray] = []
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < duration_sec:
            try:
                recorded.append(self._audio_queue.get(timeout=0.1)[0])
            except queue.Empty:
                continue
        if not recorded:
            return None
        return self.transcribe_audio(np.concatenate(recorded, axis=0).flatten())

    def start_recording(self) -> None:
        self.start_stream()
        self._test_chunks = []
        self._drain_audio_queue()

    def stop_recording_and_transcribe(self) -> Optional[str]:
        chunks = [*getattr(self, "_test_chunks", []), *self._drain_audio_queue()]
        return self.transcribe_audio(np.concatenate(chunks, axis=0).flatten()) if chunks else None

    def pause_listening(self) -> None:
        self._is_paused = True
        self._drain_audio_queue()

    def resume_listening(self) -> None:
        self._drain_audio_queue()
        self._pre_buffer.clear()
        self._is_paused = False

    def close(self) -> None:
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except (sd.PortAudioError, OSError, RuntimeError):
                pass
            self._stream = None

    def is_muted(self) -> bool:
        return self._is_muted

    def toggle_mute(self) -> bool:
        self._is_muted = not self._is_muted
        if self._is_muted:
            play_beep(500, 70)
        else:
            play_beep(1200, 40)
            time.sleep(0.04)
            play_beep(1500, 40)
        return self._is_muted

    def mute(self) -> None:
        if not self._is_muted:
            self.toggle_mute()

    def unmute(self) -> None:
        if self._is_muted:
            self.toggle_mute()

    def _start_hotkey_listener(self) -> None:
        self._hotkey_monitor.start(is_running=lambda: self._running, on_toggle=self.toggle_mute)

    def stop_ptt_loop(self) -> None:
        self._running = False

    def listen_ptt_loop(
        self, on_press_callback: Callable[[], None], on_release_callback: Callable[[str], None]
    ) -> None:
        self._running = True
        self.start_stream()
        self.init_vad()
        self._start_hotkey_listener()
        is_recording = False
        recorded: list[np.ndarray] = []
        speech_start = 0.0
        last_voice = 0.0
        speech_blocks = 0
        silence_timeout = getattr(self.config, "silence_duration_sec", 1.6)

        while self._running:
            try:
                chunk, _ = self._audio_queue.get(timeout=0.02)
            except queue.Empty:
                continue
            if self._is_paused or self._is_muted:
                continue
            prob = self.get_speech_probability(chunk)
            if not is_recording:
                if prob < 0.50:
                    speech_blocks = 0
                    self._pre_buffer.append(chunk)
                    continue
                speech_blocks += 1
                if speech_blocks >= 2 or prob >= 0.75:
                    is_recording = True
                    speech_blocks = 0
                    speech_start = time.perf_counter()
                    last_voice = speech_start
                    play_beep(1200, 40)
                    recorded = [*self._pre_buffer, chunk]
                    try:
                        on_press_callback()
                    except RuntimeError:
                        pass
            else:
                recorded.append(chunk)
                if prob >= 0.35:
                    last_voice = time.perf_counter()
                if time.perf_counter() - last_voice >= silence_timeout:
                    is_recording = False
                    play_beep(800, 40)
                    if (last_voice - speech_start) >= self.config.min_duration_sec and recorded:
                        self._finalize_speech(recorded, on_release_callback)
                    recorded = []

    def _finalize_speech(self, chunks: list[np.ndarray], on_release: Callable[[str], None]) -> None:
        t_start = time.perf_counter()
        transcript = self.transcribe_audio(np.concatenate(chunks, axis=0).flatten())
        t_lat = (time.perf_counter() - t_start) * 1000
        if not transcript:
            return
        log_event("AudioWorker", "transcribe_speech", latency_ms=t_lat, user_prompt=transcript)
        wake = self.config.wake_word
        if not wake or wake.lower() in transcript.lower():
            on_release(transcript)


__all__ = ["AudioListener", "ListenerConfig", "_setup_cuda_dlls", "play_beep"]
