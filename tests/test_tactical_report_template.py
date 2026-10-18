"""Focused unit tests for tactical report HTML template loading and fallbacks."""

from pathlib import Path
import pytest

from abi_coach.infrastructure.resources.templates import load_tactical_report_template


def test_tactical_report_template_loading():
    """Verify HTML template loads from resource path and contains expected markers."""
    template = load_tactical_report_template()
    assert "{title}" in template
    assert "{content}" in template
    assert "{timestamp}" in template
    assert "Content-Security-Policy" in template
    assert "cdn.jsdelivr.net/npm/chart.js" in template
    assert "max-width: 960px;" in template
    assert "margin: 0 auto;" in template
    assert "max-height: 320px;" in template
    assert "max-width: 920px;" in template


def test_tactical_report_template_fallback_filesystem(monkeypatch):
    """Verify template loader falls back to filesystem traversal when importlib fails."""
    import importlib.resources

    def raise_resource_error(*args, **kwargs):
        raise FileNotFoundError("Mock resource not found")

    monkeypatch.setattr(importlib.resources, "files", raise_resource_error)
    load_tactical_report_template.cache_clear()
    template = load_tactical_report_template()
    assert "{title}" in template
    assert "max-width: 960px;" in template
    load_tactical_report_template.cache_clear()


def test_tactical_report_template_repo_candidate_resolution(monkeypatch):
    """Verify repo_candidates resolution when earlier tiers fail."""
    import abi_coach.infrastructure.resources.templates as tmpl
    import importlib.resources

    def raise_resource_error(*args, **kwargs):
        raise FileNotFoundError("Mock resource failure")

    monkeypatch.setattr(importlib.resources, "files", raise_resource_error)

    orig_is_file = Path.is_file
    call_tracker = {"count": 0}

    def mock_is_file(self):
        if self.name == "tactical_report.html":
            call_tracker["count"] += 1
            if call_tracker["count"] == 1:
                return False
        return orig_is_file(self)

    monkeypatch.setattr(Path, "is_file", mock_is_file)

    tmpl.load_tactical_report_template.cache_clear()
    loaded = tmpl.load_tactical_report_template()
    assert "{title}" in loaded
    assert call_tracker["count"] >= 2
    tmpl.load_tactical_report_template.cache_clear()
