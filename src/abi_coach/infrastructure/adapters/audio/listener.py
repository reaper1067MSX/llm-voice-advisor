"""Audio input and speech-to-text listener for ABI Coach (Core Audio).

Powered by:
1. Silero VAD (Neuronal Voice Activity Detection via ONNX): High-precision speech discrimination
   that eliminates false activations from mechanical keyboards, mouse clicks, and breathing.
2. Continuous Hands-Free Listening: Smooth conversational flow with natural silence timeouts.
3. Local faster-whisper running on NVIDIA CUDA with automatic CPU fallback.
"""

import collections
import os
import queue
import threading
import time
from typing import Any, Callable, Optional
from faster_whisper import WhisperModel
import numpy as np
import sounddevice as sd

from abi_coach.infrastructure.adapters.logging.structured_logger import log_event, log_exception
from abi_coach.infrastructure.config.settings import ListenerConfig


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
        import ctypes
        import sys

        candidate_dirs = []
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            candidate_dirs.append(exe_dir)
            internal_dir = os.path.join(exe_dir, "_internal")
            if os.path.isdir(internal_dir):
                candidate_dirs.append(internal_dir)
                for root, dirs, _ in os.walk(internal_dir):
                    if any(name in root.lower() for name in ["cublas", "cudnn", "ctranslate2", "nvidia"]):
                        candidate_dirs.append(root)

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
    """High-performance audio listener with neural Silero VAD and Whisper STT."""

    def __init__(self, config: ListenerConfig):
        self.config = config
        self._running = False
        self._is_paused = False
        self._is_muted = False
        self._stream: Optional[sd.InputStream] = None
        self._whisper: Optional[WhisperModel] = None
        self._vad_model: Optional[Any] = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=300)
        # Pre-buffer keeps the last ~320ms (10 chunks of 32ms) to never clip initial speech
        self._pre_buffer = collections.deque(maxlen=10)

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
        except Exception as exc:
            log_exception("AudioWorker", "init_whisper_gpu", exc)
            # Fallback to CPU if CUDA initialization fails
            self._whisper = WhisperModel(
                self.config.whisper_model,
                device="cpu",
                compute_type="int8",
            )

        return self._whisper

    def init_vad(self) -> Optional[Any]:
        """Load Silero VAD model via faster-whisper's bundled ONNX runtime session."""
        if self._vad_model is not None:
            return self._vad_model

        try:
            from faster_whisper.vad import get_vad_model
            self._vad_model = get_vad_model()
            log_event("AudioWorker", "init_silero_vad", status="loaded")
        except Exception as exc:
            log_exception("AudioWorker", "init_silero_vad", exc)
            self._vad_model = None

        return self._vad_model

    def get_speech_probability(self, chunk: np.ndarray) -> float:
        """Evaluate voice activity probability using neural Silero VAD with fallback to RMS."""
        vad = self.init_vad()
        if vad is not None:
            try:
                flat_chunk = chunk.flatten().astype(np.float32)
                # Silero VAD requires chunks of exactly 512 samples at 16000Hz (32ms)
                if flat_chunk.shape[0] != 512:
                    if flat_chunk.shape[0] < 512:
                        flat_chunk = np.pad(flat_chunk, (0, 512 - flat_chunk.shape[0]))
                    else:
                        flat_chunk = flat_chunk[:512]
                prob = float(vad(flat_chunk)[0])
                return prob
            except Exception:
                pass

        # Robust energy fallback if neural VAD is unavailable
        rms = float(np.sqrt(np.mean(chunk**2)))
        return 1.0 if rms >= getattr(self.config, "vad_threshold", 0.02) else 0.0

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
            log_exception("AudioWorker", "transcribe_gpu_fallback", e)
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
                log_exception("AudioWorker", "transcribe_cpu_failed", e_cpu)
                print(f"❌ Error al transcribir en CPU: {e_cpu}", flush=True)
                return None

    def _audio_callback(self, indata, frames, time_info, status):
        """Warm stream callback: queues audio blocks for real-time VAD processing."""
        chunk = indata.copy().flatten()
        rms = float(np.sqrt(np.mean(chunk**2)))
        try:
            self._audio_queue.put_nowait((chunk, rms))
        except queue.Full:
            pass

    def start_stream(self) -> None:
        """Open and keep active a persistent warm InputStream with native 512-sample blocks."""
        if self._stream is None:
            try:
                self._stream = sd.InputStream(
                    samplerate=self.config.sample_rate,
                    channels=1,
                    blocksize=512,  # 512 samples = 32ms at 16000Hz (native Silero VAD frame size)
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self._stream.start()
            except Exception as e:
                log_exception("AudioWorker", "start_stream", e)
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

    def is_muted(self) -> bool:
        """Return whether microphone listening is currently muted."""
        return self._is_muted

    def toggle_mute(self) -> bool:
        """Toggle microphone mute state with distinct acoustic feedback."""
        self._is_muted = not self._is_muted
        if self._is_muted:
            play_beep(500, 70)  # Tono grave de silenciado
            key_name = getattr(self.config, "mute_key", "f10").upper()
            print(f"\n🔇 [MICRÓFONO EN SILENCIO] Escucha desactivada (Presiona {key_name} para reactivar)", flush=True)
        else:
            play_beep(1200, 40)
            time.sleep(0.04)
            play_beep(1500, 40)  # Tono agudo doble de reactivación
            print("\n🎙️ [MICRÓFONO ACTIVO] Escuchando nuevamente...", flush=True)
        return self._is_muted

    def mute(self) -> None:
        """Explicitly mute microphone listening."""
        if not self._is_muted:
            self.toggle_mute()

    def unmute(self) -> None:
        """Explicitly unmute microphone listening."""
        if self._is_muted:
            self.toggle_mute()

    def _start_hotkey_listener(self) -> None:
        """Start a background daemon thread monitoring the global mute hotkey on Windows."""
        if os.name != "nt":
            return

        import ctypes
        user32 = ctypes.windll.user32

        vk_map = {
            "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
            "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
            "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
        }
        mute_key = getattr(self.config, "mute_key", "f10").lower().strip()
        vk_code = vk_map.get(mute_key, 0x79)

        def _worker():
            was_down = False
            while self._running:
                try:
                    is_down = (user32.GetAsyncKeyState(vk_code) & 0x8000) != 0
                    if is_down and not was_down:
                        was_down = True
                        self.toggle_mute()
                    elif not is_down and was_down:
                        was_down = False
                except Exception:
                    pass
                time.sleep(0.04)

        t = threading.Thread(target=_worker, name="mute_hotkey_listener", daemon=True)
        t.start()

    def stop_ptt_loop(self) -> None:
        """Signal the listening loop to terminate."""
        self._running = False

    def listen_ptt_loop(
        self,
        on_press_callback: Callable[[], None],
        on_release_callback: Callable[[str], None],
    ) -> None:
        """Main hands-free listening loop powered by Silero VAD.
        
        Filters out breathing, keyboard typing, and ambient noise.
        Retains method signature for backward compatibility with application loop.
        """
        self._running = True
        self.start_stream()
        self.init_vad()
        self._start_hotkey_listener()

        is_recording = False
        recorded_chunks = []
        speech_start_time = 0.0
        last_voice_time = 0.0
        consecutive_speech_blocks = 0
        silence_timeout = getattr(self.config, "silence_duration_sec", 1.6)

        while self._running:
            try:
                chunk, rms = self._audio_queue.get(timeout=0.02)
            except queue.Empty:
                continue

            if self._is_paused or self._is_muted:
                continue

            prob = self.get_speech_probability(chunk)
            is_speech = prob >= 0.50

            if not is_recording:
                if is_speech:
                    consecutive_speech_blocks += 1
                    # Require 2 consecutive frames (~64ms) or high confidence (>0.75) to start recording
                    if consecutive_speech_blocks >= 2 or prob >= 0.75:
                        is_recording = True
                        consecutive_speech_blocks = 0
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
                    consecutive_speech_blocks = 0
                    self._pre_buffer.append(chunk)

            elif is_recording:
                recorded_chunks.append(chunk)
                # Lower threshold (0.35) during active speech preserves quiet syllables and word endings
                if prob >= 0.35:
                    last_voice_time = time.perf_counter()

                silence_duration = time.perf_counter() - last_voice_time
                if silence_duration >= silence_timeout:
                    is_recording = False
                    speech_duration = last_voice_time - speech_start_time
                    now_str = time.strftime("%H:%M:%S")
                    play_beep(800, 40)

                    if speech_duration < self.config.min_duration_sec or not recorded_chunks:
                        recorded_chunks = []
                        continue

                    print(f"[{now_str}] 🛑 [FIN DE VOZ] ({speech_duration:.1f}s). Transcribiendo con Whisper GPU...", flush=True)
                    audio_data = np.concatenate(recorded_chunks, axis=0).flatten()
                    recorded_chunks = []

                    t_start = time.perf_counter()
                    transcript = self.transcribe_audio(audio_data)
                    t_lat = (time.perf_counter() - t_start) * 1000

                    if transcript:
                        log_event(
                            component="AudioWorker",
                            action="transcribe_speech",
                            latency_ms=t_lat,
                            user_prompt=transcript,
                        )
                        # Optional wake word filter
                        if self.config.wake_word:
                            if self.config.wake_word.lower() not in transcript.lower():
                                print(f"[{now_str}] ℹ️ Ignorado (no contiene palabra clave '{self.config.wake_word}'): \"{transcript}\"", flush=True)
                                continue
                        on_release_callback(transcript)
                    else:
                        print(f"[{now_str}] ⚠️ No se reconoció texto claro en la grabación.", flush=True)
                        print(f"[{now_str}] 🎧 Esperando tu pregunta (habla naturalmente en tu micro)...\n", flush=True)
