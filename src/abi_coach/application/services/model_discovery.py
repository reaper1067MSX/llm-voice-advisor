"""Model Discovery Service for dynamic AI model inventory and endpoint detection.

Discovers active generative models and verifies provider connectivity across
Gemini, Moonshot (Kimi), and NVIDIA NIM.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("abi_coach.model_discovery")


@dataclass(frozen=True)
class DiscoveredModelsReport:
    """Report of discovered AI models, API availability, and active endpoints."""

    gemini_models: List[str] = field(default_factory=list)
    moonshot_available: bool = False
    nvidia_available: bool = False
    moonshot_base_url: str = "https://api.moonshot.ai/v1"
    moonshot_model: str = "kimi-k2.6"
    moonshot_models: List[str] = field(default_factory=list)

    def has_any_provider(self) -> bool:
        """Return True if at least one cloud provider is available."""
        return bool(self.gemini_models or self.moonshot_available or self.nvidia_available)

    def has_gemini(self) -> bool:
        """Return True if generative Gemini models were discovered."""
        return len(self.gemini_models) > 0

    def best_gemini_model(self, fallback: str = "gemini-3.5-flash") -> str:
        """Select optimal Gemini model prioritizing capability and latency."""
        priority_models = [
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-3.1-flash-lite-preview",
            "gemini-2.5-flash",
            "gemini-2.5-flash-preview",
        ]
        for candidate in priority_models:
            if candidate in self.gemini_models:
                return candidate
        return self.gemini_models[0] if self.gemini_models else fallback

    def build_fallback_cascade(self, include_nvidia: bool = True) -> List[str]:
        """Construct resilient fallback cascade from operational providers."""
        cascade: List[str] = []
        lite_candidates = [
            "gemini-3.1-flash-lite",
            "gemini-3.1-flash-lite-preview",
            "gemini-2.5-flash",
            "gemini-2.5-flash-preview",
        ]
        if any(c in self.gemini_models for c in lite_candidates):
            cascade.append("gemini-lite")
        if self.moonshot_available:
            cascade.append("moonshot")
        if self.nvidia_available and include_nvidia:
            cascade.append("nvidia")
        return cascade

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report to a dictionary."""
        return {
            "gemini_models": list(self.gemini_models),
            "moonshot_available": self.moonshot_available,
            "nvidia_available": self.nvidia_available,
            "moonshot_base_url": self.moonshot_base_url,
            "moonshot_model": self.moonshot_model,
            "moonshot_models": list(self.moonshot_models),
        }


class ModelDiscoveryService:
    """Discovers available models across Gemini, Moonshot, and NVIDIA."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        moonshot_api_key: Optional[str] = None,
        nvidia_api_key: Optional[str] = None,
        moonshot_base_url: str = "https://api.moonshot.ai/v1",
        moonshot_fallback_url: str = "https://api.moonshot.cn/v1",
        timeout_sec: float = 4.0,
    ):
        self.gemini_key = (
            gemini_api_key if gemini_api_key is not None else os.getenv("GEMINI_API_KEY", "")
        )
        self.moonshot_key = (
            moonshot_api_key if moonshot_api_key is not None else os.getenv("MOONSHOT_API_KEY", "")
        )
        self.nvidia_key = (
            nvidia_api_key if nvidia_api_key is not None else os.getenv("NVIDIA_API_KEY", "")
        )
        self.moonshot_base_url = moonshot_base_url.rstrip("/")
        self.moonshot_fallback_url = moonshot_fallback_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def discover(self) -> DiscoveredModelsReport:
        """Run discovery across all supported providers."""
        gemini_models = self.discover_gemini_models()
        moonshot_avail, base_url, msh_models = self.check_moonshot_connectivity()
        nvidia_avail = self.check_nvidia_availability()

        if "kimi-k2.6" in msh_models:
            chosen_model = "kimi-k2.6"
        elif msh_models:
            chosen_model = msh_models[0]
        else:
            chosen_model = "kimi-k2.6"

        return DiscoveredModelsReport(
            gemini_models=gemini_models,
            moonshot_available=moonshot_avail,
            nvidia_available=nvidia_avail,
            moonshot_base_url=base_url,
            moonshot_model=chosen_model,
            moonshot_models=msh_models,
        )

    def discover_gemini_models(self) -> List[str]:
        """Query Gemini API to filter active generative text/multimodal models."""
        if not self.gemini_key or not self.gemini_key.strip():
            return []
        try:
            from google import genai
            from google.genai import errors as genai_errors

            client = genai.Client(api_key=self.gemini_key)
            active_models: List[str] = []
            for m in client.models.list():
                raw_name = getattr(m, "name", "") or ""
                if not raw_name:
                    continue
                model_id = raw_name.replace("models/", "").strip()
                if "gemini" not in model_id.lower():
                    continue

                actions = getattr(m, "supported_actions", None)
                if actions is None or "generateContent" in actions:
                    active_models.append(model_id)

            priority_order = [
                "gemini-3.5-flash",
                "gemini-3.1-flash-lite",
                "gemini-3.1-flash-lite-preview",
                "gemini-2.5-flash",
                "gemini-2.5-flash-preview",
            ]

            def sort_key(mid: str) -> Tuple[int, Any]:
                if mid in priority_order:
                    return (0, priority_order.index(mid))
                return (1, mid) if "flash" in mid else (2, mid)

            active_models.sort(key=sort_key)
            return active_models
        except (
            genai_errors.APIError,
            httpx.HTTPError,
            ValueError,
            TypeError,
            AttributeError,
            RuntimeError,
            OSError,
            ImportError,
        ) as e:
            logger.warning(f"Error descubriendo modelos Gemini: {e}")
            return []

    def check_moonshot_connectivity(self) -> Tuple[bool, str, List[str]]:
        """Verify Moonshot API connectivity with regional fallback."""
        if not self.moonshot_key or not self.moonshot_key.strip():
            return False, self.moonshot_base_url, []

        endpoints = [self.moonshot_base_url, self.moonshot_fallback_url]
        headers = {
            "Authorization": f"Bearer {self.moonshot_key}",
            "Content-Type": "application/json",
        }

        for base_url in endpoints:
            try:
                with httpx.Client(timeout=self.timeout_sec) as client:
                    resp = client.get(f"{base_url}/models", headers=headers)
                    if resp.status_code == 200:
                        raw_data = resp.json().get("data", [])
                        models = [
                            m.get("id")
                            for m in raw_data
                            if isinstance(m, dict) and m.get("id")
                        ]
                        return True, base_url, models
                    if resp.status_code == 429:
                        return True, base_url, ["kimi-k2.6"]
            except (httpx.HTTPError, ValueError, KeyError, OSError) as e:
                logger.debug(f"Moonshot endpoint {base_url} falló: {e}")
                continue

        return False, self.moonshot_base_url, []

    def check_nvidia_availability(self) -> bool:
        """Check if NVIDIA NIM API key is configured."""
        return bool(self.nvidia_key and self.nvidia_key.strip())
