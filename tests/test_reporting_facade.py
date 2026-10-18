"""Focused unit tests for reporting facade and layer isolation."""

import inspect
from pathlib import Path
import pytest

from abi_coach.application.slices.reporting.reports import (
    HTML_TEMPLATE,
    _bring_browser_to_front_worker,
    _find_browser,
    create_html_report,
    create_tactical_dashboard,
    open_and_maximize_in_browser,
    open_and_maximize_in_chrome,
)


def test_reporting_facade_backward_compatibility():
    """Verify all legacy imports and signatures remain intact on reports.py."""
    assert callable(_find_browser)
    assert callable(open_and_maximize_in_browser)
    assert open_and_maximize_in_chrome == open_and_maximize_in_browser
    assert callable(create_html_report)
    assert callable(create_tactical_dashboard)
    assert isinstance(HTML_TEMPLATE, str)
    assert "max-width: 960px;" in HTML_TEMPLATE

    sig = inspect.signature(_bring_browser_to_front_worker)
    assert list(sig.parameters.keys()) == ["browser_type", "title_query", "focus_browser"]
    assert sig.parameters["focus_browser"].default is False


def test_reporting_facade_loc_and_no_ctypes():
    """Verify reports.py is <= 120 lines and contains zero ctypes calls."""
    reports_file = Path("src/abi_coach/application/slices/reporting/reports.py")
    assert reports_file.exists()

    content = reports_file.read_text(encoding="utf-8")
    lines = content.splitlines()

    assert len(lines) <= 120, f"reports.py has {len(lines)} LOC, exceeding 120 LOC limit!"
    assert "import ctypes" not in content, "reports.py must not import ctypes!"
    assert "from ctypes" not in content, "reports.py must not import from ctypes!"
    assert "windll" not in content, "reports.py must not reference windll!"


def test_zero_ctypes_in_all_application_slices():
    """Verify that zero files in application layer reference ctypes or windll."""
    app_dir = Path("src/abi_coach/application")
    violations = []
    for py_file in app_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if "ctypes" in text or "windll" in text or "wintypes" in text:
            violations.append(str(py_file.relative_to(app_dir)))

    assert not violations, f"Found ctypes/windll references in application layer: {violations}"
