"""Whisper speech-to-text transcriber with CUDA DLL setup and CPU fallback."""

import os
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from abi_coach.infrastructure.adapters.logging.structured_logger import log_exception
from abi_coach.infrastructure.config.settings import ListenerConfig

CUDA_PRELOAD_DLLS: tuple[str, ...] = (
    "cublas64_12.dll",
    "cublasLt64_12.dll",
    "cudnn64_9.dll",
    "cudnn_ops64_9.dll",
)


def _setup_cuda_dlls() -> None:
    """Add virtualenv NVIDIA DLL paths to Windows DLL search directory and preload them."""
    if os.name != "nt":
        return

    import ctypes
    import sys

    candidate_dirs: list[str] = []
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        candidate_dirs.append(exe_dir)
        internal_dir = os.path.join(exe_dir, "_internal")
        if os.path.isdir(internal_dir):
            candidate_dirs.append(internal_dir)
            for root, _, _ in os.walk(internal_dir):
                if any(
                    name in root.lower() for name in ("cublas", "cudnn", "ctranslate2", "nvidia")
                ):
                    candidate_dirs.append(root)

    for path_entry in sys.path:
        if "site-packages" in path_entry:
            nvidia_dir = os.path.join(path_entry, "nvidia")
            if os.path.isdir(nvidia_dir):
                for sub in ("cublas", "cudnn", "cuda_nvrtc"):
                    bin_dir = os.path.join(nvidia_dir, sub, "bin")
                    if os.path.isdir(bin_dir):
                        candidate_dirs.append(bin_dir)
            ct2_dir = os.path.join(path_entry, "ctranslate2")
            if os.path.isdir(ct2_dir):
                candidate_dirs.append(ct2_dir)

    for directory in candidate_dirs:
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(directory)
            except OSError:
                pass
        current_path = os.environ.get("PATH", "")
        if directory not in current_path:
            os.environ["PATH"] = directory + os.pathsep + current_path

    for directory in candidate_dirs:
        for dll_name in CUDA_PRELOAD_DLLS:
            full_path = os.path.join(directory, dll_name)
            if os.path.isfile(full_path):
                try:
                    ctypes.CDLL(full_path)
                except OSError:
                    pass


class WhisperTranscriber:
    """Encapsulates faster-whisper model lifecycle and GPU-to-CPU fallback transcription."""

    def __init__(
        self,
        config: ListenerConfig,
        model: Optional[WhisperModel] = None,
    ) -> None:
        self.config = config
        self._model: Optional[WhisperModel] = model

    @property
    def model(self) -> Optional[WhisperModel]:
        """Return currently initialized WhisperModel instance."""
        return self._model

    @model.setter
    def model(self, value: Optional[WhisperModel]) -> None:
        self._model = value

    def init_model(self) -> WhisperModel:
        """Initialize local faster-whisper model on GPU with fallback to CPU int8."""
        if self._model is not None:
            return self._model

        _setup_cuda_dlls()
        device = self.config.whisper_device
        compute_type = self.config.whisper_compute_type

        try:
            self._model = WhisperModel(
                self.config.whisper_model,
                device=device,
                compute_type=compute_type,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            log_exception("AudioWorker", "init_whisper_gpu", exc)
            self._model = WhisperModel(
                self.config.whisper_model,
                device="cpu",
                compute_type="int8",
            )

        return self._model

    def transcribe(self, audio_data: np.ndarray) -> Optional[str]:
        """Transcribe audio with GPU acceleration and automatic CPU fallback."""
        beam_size = getattr(self.config, "whisper_beam_size", 1)
        try:
            model = self.init_model()
            segments, _ = model.transcribe(
                audio_data,
                language=self.config.language,
                vad_filter=True,
                beam_size=beam_size,
            )
            transcript = " ".join(seg.text.strip() for seg in segments).strip()
            return transcript if transcript else None
        except (OSError, RuntimeError, ValueError) as exc:
            log_exception("AudioWorker", "transcribe_gpu_fallback", exc)
            print(
                f"\n⚠️ Aviso en transcripción GPU ({exc}). Usando Whisper CPU...",
                flush=True,
            )
            try:
                self._model = WhisperModel(
                    self.config.whisper_model,
                    device="cpu",
                    compute_type="int8",
                )
                segments, _ = self._model.transcribe(
                    audio_data,
                    language=self.config.language,
                    vad_filter=True,
                    beam_size=beam_size,
                )
                transcript = " ".join(seg.text.strip() for seg in segments).strip()
                return transcript if transcript else None
            except (OSError, RuntimeError, ValueError) as exc_cpu:
                log_exception("AudioWorker", "transcribe_cpu_failed", exc_cpu)
                print(f"❌ Error al transcribir en CPU: {exc_cpu}", flush=True)
                return None
