"""Application version metadata and dynamic configuration."""

from __future__ import annotations

import importlib.metadata

DEFAULT_VERSION = "0.2.3"


def get_version() -> str:
    """Resolve application version dynamically from package metadata or default configuration."""
    try:
        return importlib.metadata.version("llm-voice-advisor")
    except Exception:
        return DEFAULT_VERSION


APP_VERSION = get_version()
