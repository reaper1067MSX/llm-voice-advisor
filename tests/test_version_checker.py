"""Unit tests for the GitHub Release version checker and terminal bulletin presenter."""

from unittest.mock import patch
import pytest

from abi_coach.infrastructure.adapters.updater.version_checker import (
    UpdateBulletin,
    check_for_updates,
    extract_release_notes_summary,
    is_newer_version,
    parse_semver,
    render_terminal_bulletin,
)


def test_parse_semver():
    assert parse_semver("v0.2.0") == (0, 2, 0)
    assert parse_semver("0.3.1") == (0, 3, 1)
    assert parse_semver("v1.10.4-rc2") == (1, 10, 4)
    assert parse_semver("") == (0, 0, 0)
    assert parse_semver("invalid") == (0, 0, 0)


def test_is_newer_version():
    assert is_newer_version("v0.3.0", "0.2.0") is True
    assert is_newer_version("0.2.1", "0.2.0") is True
    assert is_newer_version("1.0.0", "0.9.9") is True
    assert is_newer_version("0.2.0", "0.2.0") is False
    assert is_newer_version("0.1.9", "0.2.0") is False
    assert is_newer_version("v0.2.0", "0.2.0") is False


def test_extract_release_notes_summary():
    body = """# Release v0.3.0
- Soporte para nuevos mapas en Arena Breakout
* Optimización de latencia en Whisper GPU
• Corrección de compatibilidad con monitores ultrawide
Otra línea informativa
```python
print('ignore code')
```
"""
    notes = extract_release_notes_summary(body, max_lines=4)
    assert len(notes) == 4
    assert "Soporte para nuevos mapas" in notes[0]
    assert "Optimización de latencia" in notes[1]
    assert "Corrección de compatibilidad" in notes[2]
    assert "Otra línea informativa" in notes[3]


def test_render_terminal_bulletin():
    bulletin = UpdateBulletin(
        current_version="0.2.0",
        latest_version="v0.3.0",
        release_title="Release 0.3.0 - Tactical Boost",
        release_url="https://github.com/reaper1067MSX/llm-voice-advisor/releases/tag/v0.3.0",
        published_at="2026-10-16",
        notes_summary=["Nueva detección de loot", "Menor latencia de audio"],
        is_update_available=True,
    )
    rendered = render_terminal_bulletin(bulletin)
    assert "BOLETÍN DE ACTUALIZACIÓN" in rendered
    assert "v0.3.0" in rendered
    assert "v0.2.0" in rendered
    assert "Nueva detección de loot" in rendered
    assert "https://github.com/reaper1067MSX/llm-voice-advisor/releases/tag/v0.3.0" in rendered


def test_check_for_updates_when_newer_available():
    mock_payload = {
        "tag_name": "v0.3.0",
        "name": "Release v0.3.0",
        "html_url": "https://github.com/reaper1067MSX/llm-voice-advisor/releases/tag/v0.3.0",
        "published_at": "2026-10-16T12:00:00Z",
        "body": "- Nueva característica\n- Fix de audio",
    }
    with patch(
        "abi_coach.infrastructure.adapters.updater.version_checker.fetch_latest_release",
        return_value=mock_payload,
    ):
        bulletin = check_for_updates(current_version="0.2.0")
        assert bulletin is not None
        assert bulletin.latest_version == "v0.3.0"
        assert bulletin.current_version == "0.2.0"
        assert len(bulletin.notes_summary) == 2


def test_check_for_updates_when_up_to_date():
    mock_payload = {
        "tag_name": "v0.2.0",
        "name": "Release v0.2.0",
        "html_url": "https://github.com/reaper1067MSX/llm-voice-advisor/releases/tag/v0.2.0",
        "published_at": "2026-10-15T12:00:00Z",
        "body": "No changes",
    }
    with patch(
        "abi_coach.infrastructure.adapters.updater.version_checker.fetch_latest_release",
        return_value=mock_payload,
    ):
        bulletin = check_for_updates(current_version="0.2.0")
        assert bulletin is None


def test_check_for_updates_when_network_error():
    with patch(
        "abi_coach.infrastructure.adapters.updater.version_checker.fetch_latest_release",
        return_value=None,
    ):
        bulletin = check_for_updates(current_version="0.2.0")
        assert bulletin is None
