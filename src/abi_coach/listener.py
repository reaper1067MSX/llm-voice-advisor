"""Audio input and speech-to-text listener for ABI Coach.

Uses global push-to-talk (listen-only via pynput, strictly no key injection)
and faster-whisper running on NVIDIA CUDA (RTX 4070 Ti) with CPU fallback.
"""

import os
import queue
import threading
import time
from typing import Callable, Optional
from faster_whisper import WhisperModel
import numpy as np
from pynput import keyboard, mouse
import sounddevice as sd

from abi_coach.config import ListenerConfig


def _setup_cuda_dlls() -> None:
    """Add virtualenv nvidia DLL paths to Windows DLL search directory if present."""
    if os.name == "nt":
        venv_path = os.environ.get("VIRTUAL_ENV")
        if venv_path:
            lib_site = os.path.join(venv_path, "Lib", "site-packages")
            for pkg in ["nvidia_cublas_cu12", "nvidia_cudnn_cu12", "ctranslate2"]:
                bin_dir = os.path.join(lib_site, pkg, "bin")
                if os.path.isdir(bin_dir) and hasattr(os, "add_dll_directory"):
                    try:
                        os.add_dll_directory(bin_dir)
                    except Exception:
                        pass


class AudioListener:
    def __init__(self, config: ListenerConfig):
        self.config = config
        self._is_recording = False
        self._recorded_chunks = []
        self._recording_lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._whisper: Optional[WhisperModel] = None
        self._press_start_time = 0.0

    def init_whisper(self) -> WhisperModel:
        """Initialize local faster-whisper model on GPU with fallback to CPU."""
        if self._whisper is not None:
            return self._whisper

        _setup_cuda_dlls()
        device = self.config.whisper_device
        compute_type = self.config.whisper_compute_type

        try:
            self._whisper = WhisperModel(
                self.config.whisper_model,
                device=device,
                compute_type=compute_type,
            )
        except Exception:
            # Fallback to CPU if CUDA initialization fails
            self._whisper = WhisperModel(
                self.config.whisper_model,
                device="cpu",
                compute_type="int8",
            )

        return self._whisper

    def _audio_callback(self, indata, frames, time_info, status):
        """Accumulate incoming audio blocks into the buffer."""
        if self._is_recording:
            self._recorded_chunks.append(indata.copy())

    def start_recording(self) -> None:
        """Start microphone capture."""
        with self._recording_lock:
            self._recorded_chunks = []
            self._is_recording = True
            self._press_start_time = time.perf_counter()
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()

    def stop_recording_and_transcribe(self) -> Optional[str]:
        """Stop capture, validate minimum duration, and run transcription."""
        with self._recording_lock:
            if not self._is_recording:
                return None
            self._is_recording = False
            duration = time.perf_counter() - self._press_start_time
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

            if duration < self.config.min_duration_sec or not self._recorded_chunks:
                return None

            audio_data = np.concatenate(self._recorded_chunks, axis=0).flatten()

        model = self.init_whisper()
        segments, _ = model.transcribe(
            audio_data,
            language=self.config.language,
            vad_filter=True,
            beam_size=5,
        )

        transcript = " ".join(seg.text.strip() for seg in segments).strip()
        return transcript if transcript else None

    def listen_ptt_loop(
        self,
        on_press_callback: Callable[[], None],
        on_release_callback: Callable[[str], None],
    ) -> None:
        """Listen for global push-to-talk hotkey events."""
        target_key = self.config.ptt_key.lower()

        def parse_key(key) -> str:
            if hasattr(key, "name") and key.name:
                return key.name.lower()
            if hasattr(key, "char") and key.char:
                return key.char.lower()
            return str(key).lower()

        def on_press(key):
            k = parse_key(key)
            if k == target_key and not self._is_recording:
                # Trigger instant frame capture on press
                try:
                    on_press_callback()
                except Exception:
                    pass
                self.start_recording()

        def on_release(key):
            k = parse_key(key)
            if k == target_key and self._is_recording:
                transcript = self.stop_recording_and_transcribe()
                if transcript:
                    on_release_callback(transcript)

        # Setup mouse listener if enabled
        mouse_listener: Optional[mouse.Listener] = None
        if self.config.mouse_button_enabled:
            target_btn = mouse.Button.x2 if self.config.mouse_button == "x2" else mouse.Button.x1

            def on_click(x, y, button, pressed):
                if button == target_btn:
                    if pressed and not self._is_recording:
                        on_press_callback()
                        self.start_recording()
                    elif not pressed and self._is_recording:
                        transcript = self.stop_recording_and_transcribe()
                        if transcript:
                            on_release_callback(transcript)

            mouse_listener = mouse.Listener(on_click=on_click)
            mouse_listener.start()

        # Keyboard listener loop (blocking)
        with keyboard.Listener(on_press=on_press, on_release=on_release) as k_listener:
            k_listener.join()

        if mouse_listener is not None:
            mouse_listener.stop()
