"""Template resource management for tactical reports."""

from functools import lru_cache
import importlib.resources
import os
from pathlib import Path
import sys

_TEMPLATE_NAME = "tactical_report.html"


@lru_cache(maxsize=1)
def load_tactical_report_template() -> str:
    """Load the tactical HTML report template with multi-tier fallback.

    1. importlib.resources.files (standard packaging / wheel).
    2. PyInstaller sys._MEIPASS bundle lookup.
    3. Filesystem relative path to source tree.
    """
    # 1. Standard package resources (Python 3.9+)
    try:
        res = importlib.resources.files("abi_coach.infrastructure.resources.templates").joinpath(_TEMPLATE_NAME)
        return res.read_text(encoding="utf-8")
    except Exception:
        pass

    # 2. PyInstaller frozen application
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_path = Path(sys._MEIPASS) / "abi_coach" / "infrastructure" / "resources" / "templates" / _TEMPLATE_NAME
        if bundle_path.is_file():
            return bundle_path.read_text(encoding="utf-8")

    # 3. Direct filesystem traversal fallback
    local_path = Path(__file__).resolve().parent / _TEMPLATE_NAME
    if local_path.is_file():
        return local_path.read_text(encoding="utf-8")

    repo_candidates = [
        Path(__file__).resolve().parents[5] / "src" / "abi_coach" / "infrastructure" / "resources" / "templates" / _TEMPLATE_NAME,
        Path(os.getcwd()) / "src" / "abi_coach" / "infrastructure" / "resources" / "templates" / _TEMPLATE_NAME,
    ]
    for cand in repo_candidates:
        if cand.is_file():
            return cand.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Could not locate tactical report template: {_TEMPLATE_NAME}")


HTML_TEMPLATE: str = load_tactical_report_template()

__all__ = [
    "load_tactical_report_template",
    "HTML_TEMPLATE",
]
