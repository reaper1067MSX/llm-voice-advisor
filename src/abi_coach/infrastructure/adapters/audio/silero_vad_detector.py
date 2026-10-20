"""Silero VAD detector with 512-sample chunk framing and RMS energy fallback."""

from typing import Any

import numpy as np

from abi_coach.infrastructure.adapters.logging.structured_logger import (
    log_event,
    log_exception,
)

SILERO_FRAME_SAMPLES = 512


class SileroVadDetector:
    """Neural Voice Activity Detector backed by Silero VAD ONNX with RMS fallback."""

    def __init__(self, vad_model: Any | None = None) -> None:
        self._vad_model: Any | None = vad_model

    @property
    def vad_model(self) -> Any | None:
        """Return currently loaded VAD model instance, if any."""
        return self._vad_model

    @vad_model.setter
    def vad_model(self, model: Any | None) -> None:
        self._vad_model = model

    def init_vad(self) -> Any | None:
        """Load Silero VAD model via faster-whisper's bundled ONNX runtime session."""
        if self._vad_model is not None:
            return self._vad_model

        try:
            from faster_whisper.vad import get_vad_model

            self._vad_model = get_vad_model()
            log_event("AudioWorker", "init_silero_vad", status="loaded")
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            log_exception("AudioWorker", "init_silero_vad", exc)
            self._vad_model = None

        return self._vad_model

    def get_speech_probability(
        self,
        chunk: np.ndarray,
        vad_threshold: float = 0.02,
    ) -> float:
        """Evaluate voice activity probability using Silero VAD with fallback to RMS."""
        vad = self.init_vad()
        if vad is not None:
            try:
                flat_chunk = chunk.flatten().astype(np.float32)
                if flat_chunk.shape[0] != SILERO_FRAME_SAMPLES:
                    if flat_chunk.shape[0] < SILERO_FRAME_SAMPLES:
                        pad_width = SILERO_FRAME_SAMPLES - flat_chunk.shape[0]
                        flat_chunk = np.pad(flat_chunk, (0, pad_width))
                    else:
                        flat_chunk = flat_chunk[:SILERO_FRAME_SAMPLES]
                return float(vad(flat_chunk)[0])
            except (RuntimeError, TypeError, ValueError, IndexError):
                pass

        rms = float(np.sqrt(np.mean(chunk**2)))
        return 1.0 if rms >= vad_threshold else 0.0
