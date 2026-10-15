"""Unit tests for ABI Coach components (no network required)."""

from pathlib import Path
from PIL import Image
import pytest

from abi_coach.config import AppConfig, CaptureConfig, CaptureRegion, load_config
from abi_coach.reports import create_html_report
from abi_coach.speaker import Speaker


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
    assert cfg.capture.downscale_width == 1920
    assert cfg.capture.downscale_height == 1080


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
    from abi_coach.reports import _find_browser
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
    from abi_coach.brain import Turn

    history = [Turn(role="user" if i % 2 == 0 else "coach", text=f"turn{i}") for i in range(10)]

    def compute_slice(hist, max_turns: int):
        mt = max(0, max_turns)
        return hist[-mt * 2:] if mt > 0 else []

    assert len(compute_slice(history, 0)) == 0
    assert len(compute_slice(history, 1)) == 2
    assert len(compute_slice(history, 2)) == 4
    assert compute_slice(history, 2)[0].text == "turn6"



