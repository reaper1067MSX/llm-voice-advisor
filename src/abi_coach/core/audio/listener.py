"""Audio input and speech-to-text listener for ABI Coach (Core Audio).

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

from abi_coach.core.config import ListenerConfig

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
    """Add virtualenv nvidia DLL paths to Windows DLL search directory, PATH, and preload them."""
    if os.name == "nt":
        import sys

        candidate_dirs = []
        for p in sys.path:
            if "site-packages" in p:
                nvidia_dir = os.path.join(p, "nvidia")
                if os.path.isdir(nvidia_dir):
                    for sub in ["cublas", "cudnn", "cuda_nvrtc"]:
                        b = os.path.join(nvidia_dir, sub, "bin")
                        if os.path.isdir(b):
                            candidate_dirs.append(b)
                ct2_dir = os.path.join(p, "ctranslate2")
                if os.path.isdir(ct2_dir):
                    candidate_dirs.append(ct2_dir)

        for d in candidate_dirs:
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(d)
                except Exception:
                    pass
            if d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

        # Preload essential CUDA DLLs into process memory for CTranslate2
        for d in candidate_dirs:
            for dll_name in [
                "cublas64_12.dll",
                "cublasLt64_12.dll",
                "cudnn64_9.dll",
                "cudnn_ops64_9.dll",
            ]:
                full_path = os.path.join(d, dll_name)
                if os.path.isfile(full_path):
                    try:
                        ctypes.CDLL(full_path)
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

    def transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """Transcribe audio with GPU acceleration and automatic CPU fallback."""
        beam_size = getattr(self.config, "whisper_beam_size", 1)
        try:
            model = self.init_whisper()
            segments, _ = model.transcribe(
                audio_data,
                language=self.config.language,
                vad_filter=True,
                beam_size=beam_size,
            )
            transcript = " ".join(seg.text.strip() for seg in segments).strip()
            return transcript if transcript else None
        except Exception as e:
            print(f"\n⚠️ Aviso en transcripción GPU ({e}). Usando Whisper CPU...", flush=True)
            try:
                self._whisper = WhisperModel(
                    self.config.whisper_model,
                    device="cpu",
                    compute_type="int8",
                )
                segments, _ = self._whisper.transcribe(
                    audio_data,
                    language=self.config.language,
                    vad_filter=True,
                    beam_size=beam_size,
                )
                transcript = " ".join(seg.text.strip() for seg in segments).strip()
                return transcript if transcript else None
            except Exception as e_cpu:
                print(f"❌ Error al transcribir en CPU: {e_cpu}", flush=True)
                return None

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

    def record_seconds(self, duration_sec: float = 3.0) -> Optional[str]:
        """Record audio for a fixed number of seconds and transcribe it."""
        self.start_stream()
        recorded_chunks = []
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        start_time = time.perf_counter()
        while time.perf_counter() - start_time < duration_sec:
            try:
                chunk, _ = self._audio_queue.get(timeout=0.1)
                recorded_chunks.append(chunk)
            except queue.Empty:
                continue

        if not recorded_chunks:
            return None

        audio_data = np.concatenate(recorded_chunks, axis=0).flatten()
        return self.transcribe_audio(audio_data)

    def start_recording(self) -> None:
        """Start buffering audio blocks for manual recording testing."""
        self.start_stream()
        self._test_chunks = []
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def stop_recording_and_transcribe(self) -> Optional[str]:
        """Drain accumulated audio blocks and transcribe."""
        chunks = getattr(self, "_test_chunks", [])
        while not self._audio_queue.empty():
            try:
                chunk, _ = self._audio_queue.get_nowait()
                chunks.append(chunk)
            except queue.Empty:
                break
        if not chunks:
            return None
        audio_data = np.concatenate(chunks, axis=0).flatten()
        return self.transcribe_audio(audio_data)

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
                            transcript = self.transcribe_audio(audio_data)
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

                        transcript = self.transcribe_audio(audio_data)

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
