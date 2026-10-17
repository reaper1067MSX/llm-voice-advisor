"""Unit tests for ABI Coach components (no network required)."""

from pathlib import Path
from PIL import Image
import pytest

from abi_coach.application.slices.reporting.reports import create_html_report
from abi_coach.infrastructure.adapters.audio.speaker import Speaker
from abi_coach.infrastructure.config.settings import (
    AppConfig,
    CaptureConfig,
    CaptureRegion,
    load_config,
)


def test_load_default_config(tmp_path: Path):
    cfg_file = tmp_path / "test_config.yaml"
    cfg_file.write_text(
        """
gemini:
  model: "gemini-2.5-flash"
  media_resolution: "high"
listener:
  ptt_key: "f8"
speaker:
  voice: "es-MX-DaliaNeural"
""",
        encoding="utf-8",
    )

    cfg = load_config(str(cfg_file))
    assert cfg.gemini.model == "gemini-2.5-flash"
    assert cfg.listener.ptt_key == "f8"
    assert cfg.speaker.voice == "es-MX-DaliaNeural"
    assert cfg.capture.downscale_width == 1280
    assert cfg.capture.downscale_height == 720
    assert cfg.listener.whisper_beam_size == 1


def test_clean_text_for_speech():
    speaker = Speaker(AppConfig().speaker)
    raw = "**Atención**: La munición *M80* tiene mejor penetración que [M855](http://example.com).\n- Opción 1\n- Opción 2"
    clean = speaker.clean_text_for_speech(raw)

    assert "**" not in clean
    assert "*" not in clean
    assert "http" not in clean
    assert "M855" in clean
    assert "Atención: La munición M80" in clean


def test_create_html_report_injectable_opener(tmp_path: Path):
    opened_urls = []

    def fake_opener(url: str):
        opened_urls.append(url)

    report_path = create_html_report(
        title="Comparativa de Balas 7.62",
        html_body="<div class='card'><h2>Tabla</h2><p>Contenido de prueba</p></div>",
        output_dir=str(tmp_path / "reports"),
        auto_open=True,
        opener=fake_opener,
    )

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Comparativa de Balas 7.62" in content
    assert "Contenido de prueba" in content
    assert "cdn.jsdelivr.net/npm/chart.js" in content
    assert "Content-Security-Policy" in content
    assert len(opened_urls) == 1
    assert str(report_path.name) in opened_urls[0]


def test_create_html_report_sanitizes_title(tmp_path: Path):
    report_path = create_html_report(
        title="Test <script>alert(1)</script> & 'Attack'",
        html_body="<p>Body</p>",
        output_dir=str(tmp_path / "reports"),
        auto_open=False,
    )
    content = report_path.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content
    assert "Content-Security-Policy" in content


def test_capture_region_cropping():
    # Create test 2560x1440 image
    img = Image.new("RGB", (2560, 1440), color=(100, 150, 200))
    region = CaptureRegion(x=100, y=100, width=500, height=400)

    box = (
        max(0, region.x),
        max(0, region.y),
        min(img.width, region.x + region.width),
        min(img.height, region.y + region.height),
    )
    cropped = img.crop(box)

    assert cropped.size == (500, 400)


def test_downscale_aspect_ratio_preservation():
    orig_w, orig_h = 2560, 1440
    max_w, max_h = 1920, 1080

    ratio = min(max_w / orig_w, max_h / orig_h)
    new_size = (int(orig_w * ratio), int(orig_h * ratio))

    assert new_size == (1920, 1080)


def test_find_browser_order():
    from abi_coach.application.slices.reporting.reports import _find_browser
    # Default / Firefox preference
    b_type, b_path = _find_browser(preferred="firefox")
    assert b_type in ("firefox", "edge", "chrome", "default")
    if b_type != "default":
        assert b_path is not None
        assert Path(b_path).exists()

    # Edge preference
    b_type_edge, b_path_edge = _find_browser(preferred="edge")
    assert b_type_edge in ("firefox", "edge", "chrome", "default")
    if b_type_edge != "default":
        assert b_path_edge is not None
        assert Path(b_path_edge).exists()


def test_history_slice_bounds():
    from abi_coach.application.orchestration.brain import Turn

    history = [Turn(role="user" if i % 2 == 0 else "coach", text=f"turn{i}") for i in range(10)]

    def compute_slice(hist, max_turns: int):
        mt = max(0, max_turns)
        return hist[-mt * 2:] if mt > 0 else []

    assert len(compute_slice(history, 0)) == 0
    assert len(compute_slice(history, 1)) == 2
    assert len(compute_slice(history, 2)) == 4
    assert compute_slice(history, 2)[0].text == "turn6"


def test_load_preset():
    from abi_coach.application.orchestration.brain import load_preset

    abi_preset = load_preset("abi")
    assert "Arena Breakout: Infinite" in abi_preset
    assert "create_html_report" in abi_preset

    gen_preset = load_preset("generic")
    assert "Game Advisor" in gen_preset

    fallback = load_preset("unknown_game_xyz")
    assert "Game Advisor" in fallback


def test_should_inspect_screen_heuristics():
    from abi_coach.presentation.voice.loop import should_inspect_screen

    # Positive visual triggers
    assert should_inspect_screen("mira qué arma es esta") is True
    assert should_inspect_screen("observa mi pantalla por favor") is True
    assert should_inspect_screen("ves el loot del alijo") is True
    assert should_inspect_screen("cuál me llevo de estas dos") is True
    assert should_inspect_screen("vale la pena lootear este cadáver") is True

    # Negative / Strategic conceptual queries
    assert should_inspect_screen("qué munición tiene mejor penetración") is False
    assert should_inspect_screen("cómo funciona el TTK de las balas") is False
    assert should_inspect_screen("cuál es la mejor estrategia para farmear") is False


def test_focus_browser_configuration(tmp_path: Path):
    cfg_file = tmp_path / "custom_config.yaml"
    cfg_file.write_text(
        """
reports:
  focus_browser: true
  preferred_browser: "chrome"
""",
        encoding="utf-8",
    )
    cfg = load_config(str(cfg_file))
    assert cfg.reports.focus_browser is True
    assert cfg.reports.preferred_browser == "chrome"


def test_record_seconds_mocked():
    import numpy as np
    import threading
    import time
    from abi_coach.infrastructure.adapters.audio.listener import AudioListener, ListenerConfig

    config = ListenerConfig()
    listener = AudioListener(config)

    # Mock stream and transcription without hardware
    listener.start_stream = lambda: None
    listener.transcribe_audio = lambda arr: f"transcribed_{len(arr)}"

    sample_chunk = np.zeros((1024, 1), dtype=np.float32)

    def feeder():
        time.sleep(0.02)
        listener._audio_queue.put((sample_chunk, 0.05))

    t = threading.Thread(target=feeder, daemon=True)
    t.start()

    res = listener.record_seconds(duration_sec=0.15)
    assert res == "transcribed_1024"


def test_nvidia_and_llm_config_loading(tmp_path: Path):
    cfg_file = tmp_path / "nvidia_config.yaml"
    cfg_file.write_text(
        """
llm:
  provider: "nvidia"
nvidia:
  model: "meta/llama-3.2-90b-vision-instruct"
  base_url: "https://integrate.api.nvidia.com/v1"
  temperature: 0.1
  max_tokens: 300
""",
        encoding="utf-8",
    )
    cfg = load_config(str(cfg_file))
    assert cfg.llm.provider == "nvidia"
    assert cfg.nvidia.model == "meta/llama-3.2-90b-vision-instruct"
    assert cfg.nvidia.base_url == "https://integrate.api.nvidia.com/v1"
    assert cfg.nvidia.temperature == 0.1
    assert cfg.nvidia.max_tokens == 300


def test_provider_factory_missing_keys(monkeypatch):
    from abi_coach.infrastructure.adapters.llm.factory import create_llm_provider
    from abi_coach.infrastructure.config.settings import AppConfig, LLMConfig

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    gemini_cfg = AppConfig(llm=LLMConfig(provider="gemini"))
    gemini_cfg.gemini.api_key = None
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        create_llm_provider(gemini_cfg)

    nvidia_cfg = AppConfig(llm=LLMConfig(provider="nvidia"))
    nvidia_cfg.nvidia.api_key = None
    with pytest.raises(ValueError, match="NVIDIA NIM"):
        create_llm_provider(nvidia_cfg)


def test_nvidia_nim_provider_requires_openai():
    from abi_coach.infrastructure.adapters.llm.nvidia import NvidiaNIMProvider
    from abi_coach.infrastructure.config.settings import NvidiaConfig

    cfg = NvidiaConfig()
    with pytest.raises(ImportError, match="uv add openai"):
        NvidiaNIMProvider(config=cfg, api_key="test-key")


def test_brain_with_mock_provider(tmp_path: Path):
    from abi_coach.application.orchestration.brain import Brain
    from abi_coach.infrastructure.adapters.llm.base import ProviderResponse
    from abi_coach.infrastructure.config.settings import AppConfig

    call_log = {}

    class MockProvider:
        def generate(self, prompt, system_instruction, image_bytes=None, crop_bytes=None, history_text=None, tool_callback=None):
            call_log["prompt"] = prompt
            call_log["system_instruction"] = system_instruction
            call_log["history_text"] = history_text
            if tool_callback:
                tool_callback("Test Report", "<p>Report details</p>")
            return ProviderResponse(
                spoken_text="Mocked advice: use M80.",
                input_tokens=150,
                output_tokens=30,
                latency_ms=120.5,
            )

    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    brain = Brain(config=cfg, provider=MockProvider())
    response = brain.ask("¿Qué munición uso?")

    assert response.spoken_text == "Mocked advice: use M80."
    assert response.input_tokens == 150
    assert response.output_tokens == 30
    assert response.latency_ms == 120.5
    assert response.report_path is not None
    assert "Test Report" in Path(response.report_path).read_text(encoding="utf-8")
    assert call_log["prompt"] == "¿Qué munición uso?"
    assert len(brain.history) == 2
    assert brain.history[0].role == "user"
    assert brain.history[1].text == "Mocked advice: use M80."


def test_tactical_report_builder(tmp_path: Path):
    from abi_coach.application.slices.reporting.builder import TacticalReportBuilder

    builder = (
        TacticalReportBuilder(title="Comparativa Balística", game_badge="ABI Copilot")
        .add_badge("Calibre", "7.62x51mm", color="purple")
        .add_table(headers=["Bala", "Penetración"], rows=[["M80", "Tier 4"], ["M62", "Tier 5"]])
        .add_chart("chart1", "bar", ["M80", "M62"], [{"label": "Penetración", "data": [44, 53]}], title="Gráfico Balístico")
    )
    body = builder.build_body()
    assert "7.62x51mm" in body
    assert "M80" in body
    assert "Tier 5" in body
    assert 'canvas id="chart1"' in body

    report_path = builder.save_and_open(
        output_dir=str(tmp_path / "reports"),
        auto_open=False,
    )
    assert report_path.is_file()
    html_content = report_path.read_text(encoding="utf-8")
    assert "Comparativa Balística" in html_content
    assert "chart.js" in html_content.lower()
