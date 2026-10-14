"""Audio input and speech-to-text listener for ABI Coach.

Uses global push-to-talk (GetAsyncKeyState on Windows for 100% reliable hardware polling,
listen-only via pynput on other OS, strictly no key injection)
and faster-whisper running on NVIDIA CUDA (RTX 4070 Ti) with CPU fallback.
"""

import collections
import ctypes
import os
import queue
import threading
import time
from typing import Callable, Optional
from faster_whisper import WhisperModel
import numpy as np
import sounddevice as sd

from abi_coach.config import ListenerConfig

VK_MAP = {
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "scroll_lock": 0x91, "pause": 0x13,
    "x1": 0x05, "x2": 0x06,
    "v": 0x56, "t": 0x54, "c": 0x43, "x": 0x58, "z": 0x5A,
    "caps_lock": 0x14,
}


def play_beep(freq: int, duration_ms: int) -> None:
    """Non-blocking Windows system beep for instant auditory feedback."""
    if os.name == "nt":
        try:
            import winsound
            t = threading.Thread(
                target=winsound.Beep,
                args=(freq, duration_ms),
                daemon=True,
            )
            t.start()
        except Exception:
            pass


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
        self._running = False
        # Pre-buffer keeps the last ~0.25 seconds of audio so initial words are never clipped
        self._pre_buffer = collections.deque(maxlen=4)

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
        """Warm stream callback: keeps pre-buffer and records when active."""
        chunk = indata.copy()
        with self._recording_lock:
            if self._is_recording:
                self._recorded_chunks.append(chunk)
            else:
                self._pre_buffer.append(chunk)

    def start_stream(self) -> None:
        """Open and keep active a persistent warm InputStream to eliminate lag on keypress."""
        if self._stream is None:
            try:
                self._stream = sd.InputStream(
                    samplerate=self.config.sample_rate,
                    channels=1,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self._stream.start()
            except Exception as e:
                print(f"⚠️ Aviso al iniciar InputStream de micrófono: {e}")

    def start_recording(self) -> None:
        """Start recording speech into the active buffer with pre-buffer prepend."""
        with self._recording_lock:
            # Ensure warm stream is running
            if self._stream is None or not self._stream.active:
                self.start_stream()
            self._recorded_chunks = list(self._pre_buffer)
            self._is_recording = True
            self._press_start_time = time.perf_counter()

    def stop_recording_and_transcribe(self) -> Optional[str]:
        """Stop capture, validate minimum duration, and run transcription."""
        with self._recording_lock:
            if not self._is_recording:
                return None
            self._is_recording = False
            duration = time.perf_counter() - self._press_start_time

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

    def close(self) -> None:
        """Close audio streams and release hardware resources cleanly."""
        self._running = False
        with self._recording_lock:
            self._is_recording = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    def stop_ptt_loop(self) -> None:
        """Signal the PTT polling loop to terminate."""
        self._running = False

    def listen_ptt_loop(
        self,
        on_press_callback: Callable[[], None],
        on_release_callback: Callable[[str], None],
    ) -> None:
        """Listen for global push-to-talk hotkey events using GetAsyncKeyState on Windows."""
        self._running = True
        self.start_stream()

        if os.name == "nt":
            user32 = ctypes.windll.user32
            try:
                desk = user32.OpenInputDesktop(0, False, 0x01FF)
                if desk:
                    user32.SetThreadDesktop(desk)
            except Exception:
                pass

            target_key_name = self.config.ptt_key.lower()
            target_vk = VK_MAP.get(target_key_name, 0x78)  # default F9 (0x78)

            check_mouse = self.config.mouse_button_enabled
            mouse_vk = VK_MAP.get(self.config.mouse_button.lower(), 0x06)  # default X2 (0x06)

            was_down = False

            while self._running:
                is_key_down = bool(user32.GetAsyncKeyState(target_vk) & 0x8000)
                is_mouse_down = bool(check_mouse and (user32.GetAsyncKeyState(mouse_vk) & 0x8000))
                is_down = is_key_down or is_mouse_down

                if is_down and not was_down:
                    was_down = True
                    # Auditory cue: high pitch beep indicates recording started
                    play_beep(1200, 50)
                    try:
                        on_press_callback()
                    except Exception:
                        pass
                    self.start_recording()

                elif not is_down and was_down:
                    was_down = False
                    # Auditory cue: lower pitch beep indicates recording stopped
                    play_beep(800, 50)
                    press_duration = time.perf_counter() - self._press_start_time
                    transcript = self.stop_recording_and_transcribe()

                    if transcript:
                        on_release_callback(transcript)
                    elif press_duration < self.config.min_duration_sec:
                        play_beep(400, 100)
                        print(
                            f"\n⚠️ Pulsación muy rápida ({press_duration:.2f}s). "
                            f"Mantén presionado [{target_key_name.upper()}] mientras hablas y suéltalo al terminar.",
                            flush=True,
                        )

                time.sleep(0.015)  # 15ms polling = ~66 checks/sec, ~0% CPU

        else:
            # Fallback for non-Windows systems via pynput
            from pynput import keyboard

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
                    on_press_callback()
                    self.start_recording()

            def on_release(key):
                k = parse_key(key)
                if k == target_key and self._is_recording:
                    transcript = self.stop_recording_and_transcribe()
                    if transcript:
                        on_release_callback(transcript)

            with keyboard.Listener(on_press=on_press, on_release=on_release) as k_listener:
                k_listener.join()
