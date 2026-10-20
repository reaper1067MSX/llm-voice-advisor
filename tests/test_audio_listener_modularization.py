"""Isolated unit tests for AudioListener modularization (Etapa 4)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from abi_coach.infrastructure.adapters.audio.listener import AudioListener
from abi_coach.infrastructure.adapters.audio.silero_vad_detector import (
    SILERO_FRAME_SAMPLES,
    SileroVadDetector,
)
from abi_coach.infrastructure.adapters.audio.whisper_transcriber import WhisperTranscriber
from abi_coach.infrastructure.adapters.platform.win32_audio_hotkey import (
    VK_MAP,
    GlobalMuteHotkeyMonitor,
)
from abi_coach.infrastructure.config.settings import ListenerConfig


class TestSileroVadDetector:
    """Tests for SileroVadDetector framing, ONNX invocation, and RMS fallback."""

    @pytest.mark.parametrize(
        ("input_samples", "expected_prob"),
        [
            (256, 0.85),
            (512, 0.92),
            (1024, 0.64),
        ],
    )
    def test_pads_or_truncates_to_512_samples_and_invokes_onnx(
        self,
        input_samples: int,
        expected_prob: float,
    ) -> None:
        observed_shapes: list[tuple[int, ...]] = []

        def fake_vad(frame: np.ndarray) -> list[float]:
            observed_shapes.append(frame.shape)
            return [expected_prob]

        detector = SileroVadDetector(vad_model=fake_vad)
        chunk = np.ones((input_samples, 1), dtype=np.float32) * 0.1

        prob = detector.get_speech_probability(chunk, vad_threshold=0.02)

        assert prob == pytest.approx(expected_prob)
        assert observed_shapes == [(SILERO_FRAME_SAMPLES,)]

    def test_falls_back_to_rms_when_vad_raises_or_unavailable(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def failing_vad(_frame: np.ndarray) -> list[float]:
            raise RuntimeError("ONNX failure")

        detector = SileroVadDetector(vad_model=failing_vad)
        loud_chunk = np.ones(512, dtype=np.float32) * 0.05
        quiet_chunk = np.ones(512, dtype=np.float32) * 0.001

        assert detector.get_speech_probability(loud_chunk, vad_threshold=0.02) == 1.0
        assert detector.get_speech_probability(quiet_chunk, vad_threshold=0.02) == 0.0

        detector_none = SileroVadDetector(vad_model=None)
        monkeypatch.setattr(detector_none, "init_vad", lambda: None)
        assert detector_none.get_speech_probability(loud_chunk, vad_threshold=0.02) == 1.0


class TestWhisperTranscriber:
    """Tests for WhisperTranscriber GPU initialization and CPU fallback."""

    def test_init_model_falls_back_to_cpu_when_gpu_fails(self) -> None:
        cfg = ListenerConfig(
            whisper_model="small",
            whisper_device="cuda",
            whisper_compute_type="float16",
        )
        fake_cpu_model = MagicMock()
        calls: list[tuple[str, str, str]] = []

        def fake_whisper_ctor(model_name: str, device: str, compute_type: str) -> MagicMock:
            calls.append((model_name, device, compute_type))
            if device == "cuda":
                raise RuntimeError("CUDA driver missing")
            return fake_cpu_model

        with (
            patch("abi_coach.infrastructure.adapters.audio.whisper_transcriber._setup_cuda_dlls"),
            patch(
                "abi_coach.infrastructure.adapters.audio.whisper_transcriber.WhisperModel",
                side_effect=fake_whisper_ctor,
            ),
        ):
            transcriber = WhisperTranscriber(cfg)
            model = transcriber.init_model()

        assert model is fake_cpu_model
        assert calls == [
            ("small", "cuda", "float16"),
            ("small", "cpu", "int8"),
        ]

    def test_transcribe_returns_joined_segments_and_falls_back_on_gpu_error(self) -> None:
        cfg = ListenerConfig(whisper_model="small", language="es", whisper_beam_size=1)
        gpu_model = MagicMock()
        gpu_model.transcribe.side_effect = RuntimeError("cublas error")

        cpu_model = MagicMock()
        cpu_model.transcribe.return_value = (
            [SimpleNamespace(text=" Hola "), SimpleNamespace(text=" mundo ")],
            None,
        )

        transcriber = WhisperTranscriber(cfg, model=gpu_model)
        audio = np.zeros(512, dtype=np.float32)

        with patch(
            "abi_coach.infrastructure.adapters.audio.whisper_transcriber.WhisperModel",
            return_value=cpu_model,
        ):
            text = transcriber.transcribe(audio)

        assert text == "Hola mundo"
        assert transcriber.model is cpu_model


class TestGlobalMuteHotkeyMonitorAndAudioListener:
    """Tests for GlobalMuteHotkeyMonitor mapping and AudioListener delegation."""

    def test_hotkey_monitor_resolves_vk_code_and_noops_on_non_windows(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monitor = GlobalMuteHotkeyMonitor(mute_key=" F10 ")
        assert monitor.vk_code == VK_MAP["f10"]

        monkeypatch.setattr(
            "abi_coach.infrastructure.adapters.platform.win32_audio_hotkey.os.name",
            "posix",
        )
        assert monitor.start(is_running=lambda: False, on_toggle=lambda: None) is None

    def test_audio_listener_recording_pause_resume_and_mute_delegation(self) -> None:
        cfg = ListenerConfig(mute_key="f10")
        vad_mock = MagicMock(spec=SileroVadDetector)
        vad_mock.get_speech_probability.return_value = 0.91
        transcriber_mock = MagicMock(spec=WhisperTranscriber)
        transcriber_mock.transcribe.return_value = "texto de prueba"
        hotkey_mock = MagicMock(spec=GlobalMuteHotkeyMonitor)

        listener = AudioListener(
            config=cfg,
            vad_detector=vad_mock,
            transcriber=transcriber_mock,
            hotkey_monitor=hotkey_mock,
        )
        listener.start_stream = MagicMock()  # type: ignore[method-assign]

        chunk = np.ones(512, dtype=np.float32) * 0.2
        assert listener.get_speech_probability(chunk) == pytest.approx(0.91)

        listener.start_recording()
        listener._audio_queue.put_nowait((chunk, 0.2))
        assert listener.stop_recording_and_transcribe() == "texto de prueba"

        listener._audio_queue.put_nowait((chunk, 0.2))
        listener.pause_listening()
        assert listener._is_paused is True
        assert listener._audio_queue.empty()

        listener._pre_buffer.append(chunk)
        listener.resume_listening()
        assert listener._is_paused is False
        assert len(listener._pre_buffer) == 0

        with patch("abi_coach.infrastructure.adapters.audio.listener.play_beep") as beep_mock:
            listener.mute()
            assert listener.is_muted() is True
            listener.unmute()
            assert listener.is_muted() is False
            assert beep_mock.call_count == 3
