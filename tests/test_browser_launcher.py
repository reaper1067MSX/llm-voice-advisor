"""Focused unit tests for BrowserLauncher platform adapter."""

import os
import subprocess
import time
from unittest.mock import MagicMock
import pytest

from abi_coach.infrastructure.adapters.platform.browser_launcher import BrowserLauncher


def test_find_browser_preference_ordering_mocked(monkeypatch):
    """Test preference fallback resolution when mocking binary existence."""
    launcher = BrowserLauncher()

    monkeypatch.setattr("shutil.which", lambda cmd: None)
    monkeypatch.setattr("os.path.isfile", lambda p: True if "chrome.exe" in p.lower() else False)
    b_type, b_path = launcher.find_browser(preferred="firefox")
    assert b_type == "chrome"
    assert b_path is not None

    monkeypatch.setattr("os.path.isfile", lambda p: True if ("msedge.exe" in p.lower() or "firefox.exe" in p.lower()) else False)
    b_type, b_path = launcher.find_browser(preferred="edge")
    assert b_type == "edge"

    monkeypatch.setattr("os.path.isfile", lambda p: False)
    b_type, b_path = launcher.find_browser(preferred="firefox")
    assert b_type == "default"
    assert b_path is None


def test_browser_launcher_cli_arguments():
    """Verify correct flags for different browser engines."""
    ff_args = BrowserLauncher.get_browser_args("firefox", "C:\\firefox.exe", "test.html")
    assert ff_args == ["C:\\firefox.exe", "-new-window", "test.html"]

    chrome_args = BrowserLauncher.get_browser_args("chrome", "C:\\chrome.exe", "test.html")
    assert chrome_args == ["C:\\chrome.exe", "--new-window", "test.html"]

    edge_args = BrowserLauncher.get_browser_args("edge", "C:\\msedge.exe", "test.html")
    assert edge_args == ["C:\\msedge.exe", "--new-window", "test.html"]


def test_browser_launcher_launch_process(monkeypatch):
    """Verify launch_browser_process creates Popen with shell=False."""
    mock_popen = MagicMock()
    monkeypatch.setattr("subprocess.Popen", mock_popen)

    launcher = BrowserLauncher()
    launcher.launch_browser_process("firefox", "C:\\firefox.exe", "C:\\report.html")

    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert kwargs.get("shell") is False
    assert args[0] == ["C:\\firefox.exe", "-new-window", "C:\\report.html"]


def test_browser_launcher_fallbacks_and_window_manager(monkeypatch):
    """Verify window manager notification and webbrowser fallback on failure."""
    mock_popen = MagicMock()
    monkeypatch.setattr("subprocess.Popen", mock_popen)
    mock_wm = MagicMock()
    launcher = BrowserLauncher(window_manager=mock_wm)
    monkeypatch.setattr(launcher, "find_browser", lambda preferred="firefox": ("firefox", "C:\\fake\\firefox.exe"))

    success = launcher.open("C:\\report.html", title="Report", preferred="firefox")
    assert success is True
    time.sleep(0.05)
    mock_wm.bring_browser_to_front.assert_called_once()

    # Webbrowser fallback when no browser binary found
    launcher_fb = BrowserLauncher()
    monkeypatch.setattr(launcher_fb, "find_browser", lambda preferred="firefox": ("default", None))
    mock_web = MagicMock()
    monkeypatch.setattr("webbrowser.open", mock_web)
    assert launcher_fb.open("C:\\report.html") is False
    mock_web.assert_called_once_with("C:\\report.html")
