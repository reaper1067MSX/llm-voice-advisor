"""Audio input and speech-to-text listener for ABI Coach.

Supports:
1. Continuous Voice Activity Detection (VAD): Hands-free operation where the coach
   continuously listens, detects speech, captures the screen, and answers automatically.
2. Push-to-Talk (PTT) with GetAsyncKeyState on Windows (hardware polling).
3. Hybrid Mode: Both VAD and PTT key active simultaneously.
4. faster-whisper running on NVIDIA CUDA (RTX 4070 Ti) with automatic CPU fallback.
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
        self._running = False
        self._is_paused = False
        self._stream: Optional[sd.InputStream] = None
        self._whisper: Optional[WhisperModel] = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=300)
        # Pre-buffer keeps the last ~0.4s of audio blocks
        self._pre_buffer = collections.deque(maxlen=6)

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
        """Warm stream callback: computes RMS and queues audio blocks."""
        chunk = indata.copy()
        # Compute root-mean-square energy of the incoming audio block
        rms = float(np.sqrt(np.mean(chunk**2)))
        try:
            self._audio_queue.put_nowait((chunk, rms))
        except queue.Full:
            pass

    def start_stream(self) -> None:
        """Open and keep active a persistent warm InputStream."""
        if self._stream is None:
            try:
                self._stream = sd.InputStream(
                    samplerate=self.config.sample_rate,
                    channels=1,
                    blocksize=1024,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self._stream.start()
            except Exception as e:
                print(f"⚠️ Aviso al iniciar InputStream de micrófono: {e}")

    def pause_listening(self) -> None:
        """Pause VAD and audio ingestion while the Coach is speaking aloud."""
        self._is_paused = True
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def resume_listening(self) -> None:
        """Resume listening after the Coach finishes speaking."""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        self._pre_buffer.clear()
        self._is_paused = False

    def close(self) -> None:
        """Close audio streams and release hardware resources cleanly."""
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def stop_ptt_loop(self) -> None:
        """Signal the polling loop to terminate."""
        self._running = False

    def listen_ptt_loop(
        self,
        on_press_callback: Callable[[], None],
        on_release_callback: Callable[[str], None],
    ) -> None:
        """Main listening loop supporting Continuous VAD, PTT key, or Hybrid mode."""
        self._running = True
        self.start_stream()

        mode = self.config.mode.lower()
        enable_vad = mode in ("continuous", "hybrid")
        enable_ptt = mode in ("ptt", "hybrid", "continuous")  # Keep PTT available as alternative

        # Setup Windows hardware key polling
        user32 = None
        target_vk = 0x78  # F9 default
        mouse_vk = 0x06
        check_mouse = self.config.mouse_button_enabled

        if os.name == "nt":
            user32 = ctypes.windll.user32
            try:
                desk = user32.OpenInputDesktop(0, False, 0x01FF)
                if desk:
                    user32.SetThreadDesktop(desk)
            except Exception:
                pass

            target_key_name = self.config.ptt_key.lower()
            target_vk = VK_MAP.get(target_key_name, 0x78)
            mouse_vk = VK_MAP.get(self.config.mouse_button.lower(), 0x06)

        is_recording = False
        recording_type = None  # "vad" or "ptt"
        recorded_chunks = []
        speech_start_time = 0.0
        last_voice_time = 0.0
        was_ptt_down = False

        while self._running:
            # 1. Check physical hardware PTT key state (if on Windows)
            if enable_ptt and user32 is not None:
                is_key_down = bool(user32.GetAsyncKeyState(target_vk) & 0x8000)
                is_mouse_down = bool(check_mouse and (user32.GetAsyncKeyState(mouse_vk) & 0x8000))
                is_ptt_down = is_key_down or is_mouse_down

                if is_ptt_down and not was_ptt_down and not self._is_paused:
                    was_ptt_down = True
                    is_recording = True
                    recording_type = "ptt"
                    speech_start_time = time.perf_counter()
                    now_str = time.strftime("%H:%M:%S")
                    print(f"\n[{now_str}] 🎙️ [{self.config.ptt_key.upper()} PRESIONADO] Grabando y capturando pantalla...", flush=True)
                    play_beep(1200, 50)
                    recorded_chunks = list(self._pre_buffer)
                    try:
                        on_press_callback()
                    except Exception:
                        pass

                elif not is_ptt_down and was_ptt_down:
                    was_ptt_down = False
                    if recording_type == "ptt":
                        is_recording = False
                        recording_type = None
                        press_duration = time.perf_counter() - speech_start_time
                        now_str = time.strftime("%H:%M:%S")
                        play_beep(800, 50)

                        if press_duration < self.config.min_duration_sec or not recorded_chunks:
                            play_beep(400, 100)
                            print(f"[{now_str}] ⚠️ Pulsación rápida ({press_duration:.2f}s). Mantén presionado mientras hablas.", flush=True)
                        else:
                            print(f"[{now_str}] 🛑 [TECLA SOLTADA] ({press_duration:.2f}s). Transcribiendo en GPU...", flush=True)
                            audio_data = np.concatenate(recorded_chunks, axis=0).flatten()
                            recorded_chunks = []
                            model = self.init_whisper()
                            segments, _ = model.transcribe(
                                audio_data,
                                language=self.config.language,
                                vad_filter=True,
                                beam_size=5,
                            )
                            transcript = " ".join(seg.text.strip() for seg in segments).strip()
                            if transcript:
                                on_release_callback(transcript)
                            else:
                                print(f"[{now_str}] ⚠️ No se detectó voz clara.", flush=True)

            # 2. Process audio blocks from the microphone queue
            try:
                chunk, rms = self._audio_queue.get(timeout=0.02)
            except queue.Empty:
                continue

            if self._is_paused:
                continue

            # Continuous Voice Activity Detection (VAD)
            if enable_vad and recording_type != "ptt":
                is_speech = rms >= self.config.vad_threshold

                if not is_recording:
                    if is_speech:
                        # Voice detected!
                        is_recording = True
                        recording_type = "vad"
                        speech_start_time = time.perf_counter()
                        last_voice_time = time.perf_counter()
                        now_str = time.strftime("%H:%M:%S")
                        print(f"\n[{now_str}] 🎙️ [VOZ DETECTADA] Escuchando tu pregunta...", flush=True)
                        play_beep(1200, 40)
                        recorded_chunks = list(self._pre_buffer)
                        recorded_chunks.append(chunk)
                        try:
                            on_press_callback()
                        except Exception:
                            pass
                    else:
                        self._pre_buffer.append(chunk)

                elif is_recording and recording_type == "vad":
                    recorded_chunks.append(chunk)
                    if is_speech:
                        last_voice_time = time.perf_counter()

                    # Check if silence timeout reached
                    silence_duration = time.perf_counter() - last_voice_time
                    if silence_duration >= self.config.silence_duration_sec:
                        is_recording = False
                        recording_type = None
                        speech_duration = last_voice_time - speech_start_time
                        now_str = time.strftime("%H:%M:%S")
                        play_beep(800, 40)

                        if speech_duration < self.config.min_duration_sec or not recorded_chunks:
                            recorded_chunks = []
                            continue

                        print(f"[{now_str}] 🛑 [FIN DE VOZ] ({speech_duration:.1f}s). Transcribiendo con Whisper GPU...", flush=True)
                        audio_data = np.concatenate(recorded_chunks, axis=0).flatten()
                        recorded_chunks = []

                        model = self.init_whisper()
                        segments, _ = model.transcribe(
                            audio_data,
                            language=self.config.language,
                            vad_filter=True,
                            beam_size=5,
                        )
                        transcript = " ".join(seg.text.strip() for seg in segments).strip()

                        if transcript:
                            # Optional wake word filter
                            if self.config.wake_word:
                                if self.config.wake_word.lower() not in transcript.lower():
                                    print(f"[{now_str}] ℹ️ Ignorado (no contiene palabra clave '{self.config.wake_word}'): \"{transcript}\"", flush=True)
                                    continue
                            on_release_callback(transcript)
                        else:
                            print(f"[{now_str}] ⚠️ No se reconoció texto claro en la grabación.", flush=True)
                            print(f"[{now_str}] 🎧 Esperando tu pregunta (habla naturalmente en tu micro)...\n", flush=True)

            elif is_recording and recording_type == "ptt":
                recorded_chunks.append(chunk)
