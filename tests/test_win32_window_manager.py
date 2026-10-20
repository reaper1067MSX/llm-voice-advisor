"""Focused unit tests for Win32WindowManager and NullWindowManager platform adapters."""

import ctypes
from unittest.mock import MagicMock
import pytest

from abi_coach.domain.ports.window_manager_port import WindowManagerPort
from abi_coach.infrastructure.adapters.platform.win32_window_manager import (
    NullWindowManager,
    Win32WindowManager,
    bring_browser_to_front_worker,
)


def test_window_manager_port_and_null_implementation():
    """Verify WindowManagerPort protocol and NullWindowManager no-ops."""
    assert isinstance(NullWindowManager(), WindowManagerPort)
    assert isinstance(Win32WindowManager(), WindowManagerPort)

    nwm = NullWindowManager()
    assert nwm.get_secondary_monitor_bounds() is None
    assert nwm.bring_browser_to_front("firefox") is False
    assert nwm.bring_to_front("edge") is False


def test_win32_window_manager_non_windows_noop(monkeypatch):
    """Verify Win32WindowManager degrades gracefully on non-Windows platforms."""
    monkeypatch.setattr("os.name", "posix")

    wm = Win32WindowManager()
    assert wm.get_secondary_monitor_bounds() is None
    assert wm.bring_browser_to_front("firefox", "Title", focus_browser=False) is False
    bring_browser_to_front_worker("chrome", "Title", focus_browser=True)


def test_win32_window_manager_with_mock_user32(monkeypatch):
    """Verify monitor bounds enumeration with injected mock user32."""
    monkeypatch.setattr("os.name", "nt")
    mock_user32 = MagicMock()

    def fake_enum_monitors(hdc, lprcClip, lpfnEnum, dwData):
        def fake_get_mon_info(hmon, p_mi):
            mi = getattr(p_mi, "_obj", None)
            if mi is not None:
                is_primary = 1 if hmon == 1 else 0
                mi.dwFlags = is_primary
                mi.rcWork[0] = 0 if is_primary else 1920
                mi.rcWork[1] = 0
                mi.rcWork[2] = 1920 if is_primary else 3840
                mi.rcWork[3] = 1080
            return 1

        mock_user32.GetMonitorInfoW.side_effect = fake_get_mon_info
        lpfnEnum(1, 0, None, 0)
        lpfnEnum(2, 0, None, 0)
        return 1

    mock_user32.EnumDisplayMonitors.side_effect = fake_enum_monitors
    wm = Win32WindowManager(user32=mock_user32)
    assert wm.get_secondary_monitor_bounds() == (1920, 0, 1920, 1080)


def test_win32_window_manager_positioning_and_safe_output(monkeypatch, capsys):
    """Verify window positioning, ShowWindow calls, and CP1252-safe output."""
    monkeypatch.setattr("os.name", "nt")
    mock_user32 = MagicMock()
    mock_user32.IsWindowVisible.return_value = 1
    mock_user32.IsIconic.return_value = 1

    def fake_get_class_name(hwnd, buf, size):
        ctypes.memmove(buf, ctypes.create_unicode_buffer("MozillaWindowClass"), 40)
        return 1

    def fake_get_window_text(hwnd, buf, size):
        ctypes.memmove(buf, ctypes.create_unicode_buffer("Firefox - Tactical Report"), 50)
        return 1

    mock_user32.GetClassNameW.side_effect = fake_get_class_name
    mock_user32.GetWindowTextW.side_effect = fake_get_window_text
    mock_user32.EnumWindows.side_effect = lambda cb, lparam: (cb(12345, 0), 1)[1]

    wm = Win32WindowManager(user32=mock_user32)
    monkeypatch.setattr(wm, "get_secondary_monitor_bounds", lambda: (1920, 0, 1920, 1080))

    success = wm.bring_browser_to_front("firefox", "Tactical", focus_browser=True, max_retries=1, poll_interval=0.01)
    assert success is True
    mock_user32.ShowWindow.assert_any_call(12345, 9)
    mock_user32.ShowWindow.assert_any_call(12345, 3)

    captured = capsys.readouterr()
    assert "DISPLAY2" in captured.out
    assert "🌐" not in captured.out
