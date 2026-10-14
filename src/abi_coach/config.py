"""Configuration management for ABI Coach."""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import yaml


@dataclass
class GeminiConfig:
    model: str = "gemini-2.5-flash"
    media_resolution: str = "high"
    temperature: float = 0.3
    api_key: Optional[str] = None


@dataclass
class CaptureRegion:
    x: int
    y: int
    width: int
    height: int


@dataclass
class CaptureConfig:
    monitor_index: int = 1
    downscale_width: int = 1920
    downscale_height: int = 1080
    jpeg_quality: int = 85
    save_captures: bool = False
    capture_dir: str = "captures"
    regions: Dict[str, CaptureRegion] = field(default_factory=dict)


@dataclass
class ListenerConfig:
    ptt_key: str = "f9"
    mouse_button_enabled: bool = False
    mouse_button: str = "x2"
    sample_rate: int = 16000
    min_duration_sec: float = 0.4
    whisper_model: str = "large-v3-turbo"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"
    language: str = "es"


@dataclass
class SpeakerConfig:
    engine: str = "edge-tts"
    voice: str = "es-MX-DaliaNeural"
    rate: str = "+5%"
    volume: str = "+0%"


@dataclass
class ReportConfig:
    output_dir: str = "reports"
    auto_open_browser: bool = True


@dataclass
class HistoryConfig:
    max_turns: int = 5


@dataclass
class AppConfig:
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    listener: ListenerConfig = field(default_factory=ListenerConfig)
    speaker: SpeakerConfig = field(default_factory=SpeakerConfig)
    reports: ReportConfig = field(default_factory=ReportConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from YAML and environment variables."""
    load_dotenv()

    root_dir = Path(__file__).resolve().parent.parent.parent
    if config_path is None:
        target_path = root_dir / "config.yaml"
    else:
        target_path = Path(config_path)

    raw: Dict[str, Any] = {}
    if target_path.exists():
        with open(target_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    gemini_raw = raw.get("gemini", {})
    api_key = os.getenv("GEMINI_API_KEY") or gemini_raw.get("api_key")
    gemini_cfg = GeminiConfig(
        model=gemini_raw.get("model", "gemini-2.5-flash"),
        media_resolution=gemini_raw.get("media_resolution", "high"),
        temperature=float(gemini_raw.get("temperature", 0.3)),
        api_key=api_key,
    )

    cap_raw = raw.get("capture", {})
    regions_raw = cap_raw.get("regions") or {}
    regions: Dict[str, CaptureRegion] = {}
    for name, r in regions_raw.items():
        if isinstance(r, dict):
            regions[name] = CaptureRegion(
                x=int(r.get("x", 0)),
                y=int(r.get("y", 0)),
                width=int(r.get("width", 0)),
                height=int(r.get("height", 0)),
            )

    cap_cfg = CaptureConfig(
        monitor_index=int(cap_raw.get("monitor_index", 1)),
        downscale_width=int(cap_raw.get("downscale_width", 1920)),
        downscale_height=int(cap_raw.get("downscale_height", 1080)),
        jpeg_quality=int(cap_raw.get("jpeg_quality", 85)),
        save_captures=bool(cap_raw.get("save_captures", False)),
        capture_dir=str(cap_raw.get("capture_dir", "captures")),
        regions=regions,
    )

    lis_raw = raw.get("listener", {})
    lis_cfg = ListenerConfig(
        ptt_key=str(lis_raw.get("ptt_key", "f9")).lower(),
        mouse_button_enabled=bool(lis_raw.get("mouse_button_enabled", False)),
        mouse_button=str(lis_raw.get("mouse_button", "x2")).lower(),
        sample_rate=int(lis_raw.get("sample_rate", 16000)),
        min_duration_sec=float(lis_raw.get("min_duration_sec", 0.4)),
        whisper_model=str(lis_raw.get("whisper_model", "large-v3-turbo")),
        whisper_device=str(lis_raw.get("whisper_device", "cuda")),
        whisper_compute_type=str(lis_raw.get("whisper_compute_type", "float16")),
        language=str(lis_raw.get("language", "es")),
    )

    spk_raw = raw.get("speaker", {})
    spk_cfg = SpeakerConfig(
        engine=str(spk_raw.get("engine", "edge-tts")),
        voice=str(spk_raw.get("voice", "es-MX-DaliaNeural")),
        rate=str(spk_raw.get("rate", "+5%")),
        volume=str(spk_raw.get("volume", "+0%")),
    )

    rep_raw = raw.get("reports", {})
    rep_cfg = ReportConfig(
        output_dir=str(rep_raw.get("output_dir", "reports")),
        auto_open_browser=bool(rep_raw.get("auto_open_browser", True)),
    )

    his_raw = raw.get("history", {})
    his_cfg = HistoryConfig(
        max_turns=int(his_raw.get("max_turns", 5)),
    )

    return AppConfig(
        gemini=gemini_cfg,
        capture=cap_cfg,
        listener=lis_cfg,
        speaker=spk_cfg,
        reports=rep_cfg,
        history=his_cfg,
    )
