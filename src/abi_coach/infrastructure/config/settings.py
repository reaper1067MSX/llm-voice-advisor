"""Configuration management for ABI Coach (Core)."""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import yaml


@dataclass
class GeminiConfig:
    model: str = "gemini-3.5-flash"
    media_resolution: str = "medium"
    temperature: float = 0.3
    max_output_tokens: int = 250
    thinking_budget: Optional[int] = 0
    api_key: Optional[str] = None
    game: str = "generic"
    system_instruction: Optional[str] = None


@dataclass
class NvidiaConfig:
    model: str = "meta/llama-3.2-11b-vision-instruct"
    base_url: str = "https://integrate.api.nvidia.com/v1"
    temperature: float = 0.2
    max_tokens: int = 500
    api_key: Optional[str] = None
    api_key_env: str = "NVIDIA_API_KEY"


@dataclass
class MoonshotConfig:
    model: str = "moonshot-v1-8k"
    base_url: str = "https://api.moonshot.cn/v1"
    temperature: float = 0.3
    max_tokens: int = 250
    api_key: Optional[str] = None
    api_key_env: str = "MOONSHOT_API_KEY"
    timeout_sec: float = 6.0


@dataclass
class ResilienceConfig:
    enabled: bool = True
    failure_threshold: int = 2
    recovery_timeout_sec: float = 30.0
    fallback_cascade: List[str] = field(default_factory=lambda: ["gemini-lite", "moonshot"])


@dataclass
class LLMConfig:
    provider: str = "gemini"  # "gemini", "nvidia", or "resilient"


@dataclass
class CaptureRegion:
    x: int
    y: int
    width: int
    height: int


@dataclass
class CaptureConfig:
    monitor_index: int = 1
    downscale_width: int = 1280
    downscale_height: int = 720
    jpeg_quality: int = 75
    save_captures: bool = False
    capture_dir: str = "captures"
    regions: Dict[str, CaptureRegion] = field(default_factory=dict)


@dataclass
class ListenerConfig:
    mode: str = "continuous"  # "continuous" (manos libres VAD), "ptt", or "hybrid"
    ptt_key: str = "f9"
    mute_key: str = "f10"
    mouse_button_enabled: bool = False
    mouse_button: str = "x2"
    sample_rate: int = 16000
    min_duration_sec: float = 0.4
    silence_duration_sec: float = 1.6
    vad_threshold: float = 0.020
    wake_word: Optional[str] = None
    whisper_model: str = "large-v3-turbo"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"
    whisper_beam_size: int = 1
    language: str = "es"


@dataclass
class SpeakerConfig:
    engine: str = "edge-tts"
    voice: str = "es-CO-SalomeNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"


@dataclass
class ReportConfig:
    output_dir: str = "reports"
    auto_open_browser: bool = True
    preferred_browser: str = "firefox"  # "firefox", "edge", or "chrome"
    focus_browser: bool = False


@dataclass
class HistoryConfig:
    max_turns: int = 5


@dataclass
class AppConfig:
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    nvidia: NvidiaConfig = field(default_factory=NvidiaConfig)
    moonshot: MoonshotConfig = field(default_factory=MoonshotConfig)
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    listener: ListenerConfig = field(default_factory=ListenerConfig)
    speaker: SpeakerConfig = field(default_factory=SpeakerConfig)
    reports: ReportConfig = field(default_factory=ReportConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)


import sys


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from YAML and environment variables, supporting frozen exe and dedicated keys file."""
    # 1. Determine root application directory
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        cur = Path(__file__).resolve()
        base_dir = None
        for p in cur.parents:
            if (p / "config.yaml").is_file() or (p / "pyproject.toml").is_file():
                base_dir = p
                break
        if base_dir is None:
            base_dir = cur.parents[3]

    # 2. Search and load keys from keys.env, .env in base_dir and CWD
    env_candidates = [
        base_dir / "keys.env",
        base_dir / ".env",
        Path.cwd() / "keys.env",
        Path.cwd() / ".env",
    ]
    for env_path in env_candidates:
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path, override=False)

    # 3. Check for simplified keys.yaml in base_dir and CWD
    for key_yaml in [base_dir / "keys.yaml", Path.cwd() / "keys.yaml"]:
        if key_yaml.is_file():
            try:
                with open(key_yaml, "r", encoding="utf-8") as f:
                    k_data = yaml.safe_load(f) or {}
                    if "gemini_api_key" in k_data and not os.getenv("GEMINI_API_KEY"):
                        os.environ["GEMINI_API_KEY"] = str(k_data["gemini_api_key"]).strip()
                    if "nvidia_api_key" in k_data and not os.getenv("NVIDIA_API_KEY"):
                        os.environ["NVIDIA_API_KEY"] = str(k_data["nvidia_api_key"]).strip()
                    if "moonshot_api_key" in k_data and not os.getenv("MOONSHOT_API_KEY"):
                        os.environ["MOONSHOT_API_KEY"] = str(k_data["moonshot_api_key"]).strip()
            except Exception:
                pass

    # 4. Resolve target config.yaml path
    if config_path is None:
        target_path = base_dir / "config.yaml"
    else:
        target_path = Path(config_path)

    raw: Dict[str, Any] = {}
    if target_path.exists():
        with open(target_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    gemini_raw = raw.get("gemini", {})
    api_key = os.getenv("GEMINI_API_KEY") or gemini_raw.get("api_key")
    gemini_cfg = GeminiConfig(
        model=gemini_raw.get("model", "gemini-3.1-flash-lite-preview"),
        media_resolution=gemini_raw.get("media_resolution", "medium"),
        temperature=float(gemini_raw.get("temperature", 0.3)),
        api_key=api_key,
        game=str(gemini_raw.get("game", "generic")).lower(),
        system_instruction=gemini_raw.get("system_instruction"),
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
        downscale_width=int(cap_raw.get("downscale_width", 1280)),
        downscale_height=int(cap_raw.get("downscale_height", 720)),
        jpeg_quality=int(cap_raw.get("jpeg_quality", 75)),
        save_captures=bool(cap_raw.get("save_captures", False)),
        capture_dir=str(cap_raw.get("capture_dir", "captures")),
        regions=regions,
    )

    lis_raw = raw.get("listener", {})
    lis_cfg = ListenerConfig(
        mode=str(lis_raw.get("mode", "continuous")).lower(),
        ptt_key=str(lis_raw.get("ptt_key", "f9")).lower(),
        mute_key=str(lis_raw.get("mute_key", "f10")).lower(),
        mouse_button_enabled=bool(lis_raw.get("mouse_button_enabled", False)),
        mouse_button=str(lis_raw.get("mouse_button", "x2")).lower(),
        sample_rate=int(lis_raw.get("sample_rate", 16000)),
        min_duration_sec=float(lis_raw.get("min_duration_sec", 0.4)),
        silence_duration_sec=float(lis_raw.get("silence_duration_sec", 1.6)),
        vad_threshold=float(lis_raw.get("vad_threshold", 0.020)),
        wake_word=lis_raw.get("wake_word"),
        whisper_model=str(lis_raw.get("whisper_model", "large-v3-turbo")),
        whisper_device=str(lis_raw.get("whisper_device", "cuda")),
        whisper_compute_type=str(lis_raw.get("whisper_compute_type", "float16")),
        whisper_beam_size=int(lis_raw.get("whisper_beam_size", 1)),
        language=str(lis_raw.get("language", "es")),
    )

    spk_raw = raw.get("speaker", {})
    spk_cfg = SpeakerConfig(
        engine=str(spk_raw.get("engine", "edge-tts")),
        voice=str(spk_raw.get("voice", "es-CO-SalomeNeural")),
        rate=str(spk_raw.get("rate", "+0%")),
        volume=str(spk_raw.get("volume", "+0%")),
        pitch=str(spk_raw.get("pitch", "+0Hz")),
    )

    rep_raw = raw.get("reports", {})
    rep_cfg = ReportConfig(
        output_dir=str(rep_raw.get("output_dir", "reports")),
        auto_open_browser=bool(rep_raw.get("auto_open_browser", True)),
        preferred_browser=str(rep_raw.get("preferred_browser", "firefox")).lower(),
        focus_browser=bool(rep_raw.get("focus_browser", False)),
    )

    his_raw = raw.get("history", {})
    his_cfg = HistoryConfig(
        max_turns=int(his_raw.get("max_turns", 5)),
    )

    llm_raw = raw.get("llm", {})
    llm_cfg = LLMConfig(
        provider=str(llm_raw.get("provider", "gemini")).lower().strip()
    )

    nvd_raw = raw.get("nvidia", {})
    nvd_key_env = str(nvd_raw.get("api_key_env", "NVIDIA_API_KEY"))
    nvd_cfg = NvidiaConfig(
        model=str(nvd_raw.get("model", "meta/llama-3.2-11b-vision-instruct")),
        base_url=str(nvd_raw.get("base_url", "https://integrate.api.nvidia.com/v1")),
        temperature=float(nvd_raw.get("temperature", 0.2)),
        max_tokens=int(nvd_raw.get("max_tokens", 500)),
        api_key=nvd_raw.get("api_key") or os.getenv(nvd_key_env),
        api_key_env=nvd_key_env,
    )

    msh_raw = raw.get("moonshot", {})
    msh_key_env = str(msh_raw.get("api_key_env", "MOONSHOT_API_KEY"))
    msh_cfg = MoonshotConfig(
        model=str(msh_raw.get("model", "moonshot-v1-8k")),
        base_url=str(msh_raw.get("base_url", "https://api.moonshot.cn/v1")),
        temperature=float(msh_raw.get("temperature", 0.3)),
        max_tokens=int(msh_raw.get("max_tokens", 250)),
        api_key=msh_raw.get("api_key") or os.getenv(msh_key_env),
        api_key_env=msh_key_env,
        timeout_sec=float(msh_raw.get("timeout_sec", 6.0)),
    )

    res_raw = raw.get("resilience", {})
    res_cfg = ResilienceConfig(
        enabled=bool(res_raw.get("enabled", True)),
        failure_threshold=int(res_raw.get("failure_threshold", 2)),
        recovery_timeout_sec=float(res_raw.get("recovery_timeout_sec", 30.0)),
        fallback_cascade=list(res_raw.get("fallback_cascade", ["gemini-lite", "moonshot"])),
    )

    return AppConfig(
        gemini=gemini_cfg,
        nvidia=nvd_cfg,
        moonshot=msh_cfg,
        resilience=res_cfg,
        llm=llm_cfg,
        capture=cap_cfg,
        listener=lis_cfg,
        speaker=spk_cfg,
        reports=rep_cfg,
        history=his_cfg,
    )
