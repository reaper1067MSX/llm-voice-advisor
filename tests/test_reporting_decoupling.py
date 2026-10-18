"""Unit tests for Decoupled Reporting, Platform Adapters, and Template Loading.

Verifies:
1. Externalized HTML template loading, fallbacks, and constraints.
2. BrowserLauncher discovery, CLI flags, process execution, and webbrowser fallback.
3. Win32WindowManager and NullWindowManager platform handling.
4. reports.py thin facade backward compatibility, LOC <= 120, and zero ctypes in application.
5. Tactical dashboard extraction in dashboard.py.
"""

import ctypes
import inspect
import os
from pathlib import Path
import time
from unittest.mock import MagicMock

import pytest

from abi_coach.application.slices.reporting.dashboard import create_tactical_dashboard as dashboard_create
from abi_coach.application.slices.reporting.reports import (
    HTML_TEMPLATE,
    _bring_browser_to_front_worker,
    _find_browser,
    create_html_report,
    create_tactical_dashboard,
    open_and_maximize_in_browser,
    open_and_maximize_in_chrome,
)
from abi_coach.domain.ports.window_manager_port import WindowManagerPort
from abi_coach.infrastructure.adapters.platform.browser_launcher import (
    BrowserLauncher,
    find_browser,
    open_and_maximize_in_browser as platform_open,
)
from abi_coach.infrastructure.adapters.platform.win32_window_manager import (
    NullWindowManager,
    Win32WindowManager,
    bring_browser_to_front_worker,
    get_default_window_manager,
)
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
    # Clear lru_cache to force reload
    load_tactical_report_template.cache_clear()
    template = load_tactical_report_template()
    assert "{title}" in template
    assert "max-width: 960px;" in template
    load_tactical_report_template.cache_clear()


def test_find_browser_preference_ordering_mocked(monkeypatch):
    """Test preference fallback resolution when mocking binary existence."""
    launcher = BrowserLauncher()

    # Scenario 1: Only Chrome exists
    monkeypatch.setattr("shutil.which", lambda cmd: None)
    monkeypatch.setattr(
        "os.path.isfile",
        lambda path: True if "chrome.exe" in path.lower() else False,
    )

    b_type, b_path = launcher.find_browser(preferred="firefox")
    assert b_type == "chrome"
    assert b_path is not None
    assert "chrome.exe" in b_path.lower()

    # Scenario 2: Both Edge and Firefox exist, user prefers Edge
    monkeypatch.setattr(
        "os.path.isfile",
        lambda path: True if ("msedge.exe" in path.lower() or "firefox.exe" in path.lower()) else False,
    )
    b_type, b_path = launcher.find_browser(preferred="edge")
    assert b_type == "edge"
    assert "msedge.exe" in b_path.lower()

    # Scenario 3: Chrome and Edge exist, user prefers Chrome
    monkeypatch.setattr(
        "os.path.isfile",
        lambda path: True if ("chrome.exe" in path.lower() or "msedge.exe" in path.lower()) else False,
    )
    b_type, b_path = launcher.find_browser(preferred="chrome")
    assert b_type == "chrome"
    assert "chrome.exe" in b_path.lower()

    # Scenario 4: No browsers installed
    monkeypatch.setattr("os.path.isfile", lambda path: False)
    b_type, b_path = launcher.find_browser(preferred="firefox")
    assert b_type == "default"
    assert b_path is None


def test_browser_launcher_cli_arguments():
    """Verify correct single-dash vs double-dash flags for different browser engines."""
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


def test_browser_launcher_open_with_window_manager(monkeypatch):
    """Verify launcher.open starts window manager thread when binary is found."""
    mock_popen = MagicMock()
    monkeypatch.setattr("subprocess.Popen", mock_popen)

    mock_wm = MagicMock()
    launcher = BrowserLauncher(window_manager=mock_wm)
    monkeypatch.setattr(launcher, "find_browser", lambda preferred="firefox": ("firefox", "C:\\fake\\firefox.exe"))

    success = launcher.open("C:\\report.html", title="Report", preferred="firefox")
    assert success is True
    # Give daemon thread a brief moment to execute
    time.sleep(0.05)
    mock_wm.bring_browser_to_front.assert_called_once()


def test_browser_launcher_webbrowser_fallback(monkeypatch):
    """Verify that when no browser binary exists, webbrowser.open is invoked."""
    launcher = BrowserLauncher()
    monkeypatch.setattr(launcher, "find_browser", lambda preferred="firefox": ("default", None))

    mock_webbrowser = MagicMock()
    monkeypatch.setattr("webbrowser.open", mock_webbrowser)

    success = launcher.open("C:\\report.html")
    assert success is False
    mock_webbrowser.assert_called_once_with("C:\\report.html")


def test_browser_launcher_popen_exception_fallback(monkeypatch):
    """Verify that if subprocess.Popen fails, it catches the error and uses webbrowser."""
    launcher = BrowserLauncher()
    monkeypatch.setattr(launcher, "find_browser", lambda preferred="firefox": ("chrome", "C:\\fake\\chrome.exe"))

    def raise_oserror(*args, **kwargs):
        raise OSError("Access denied")

    monkeypatch.setattr("subprocess.Popen", raise_oserror)

    mock_webbrowser = MagicMock()
    monkeypatch.setattr("webbrowser.open", mock_webbrowser)

    success = launcher.open("C:\\report.html")
    assert success is False
    mock_webbrowser.assert_called_once_with("C:\\report.html")


def test_win32_window_manager_non_windows_noop(monkeypatch):
    """Verify Win32WindowManager degrades gracefully on non-Windows platforms."""
    monkeypatch.setattr("os.name", "posix")

    wm = Win32WindowManager()
    assert wm.get_secondary_monitor_bounds() is None
    assert wm.bring_browser_to_front("firefox", "Title", focus_browser=False) is False

    # Should not raise any error
    bring_browser_to_front_worker("chrome", "Title", focus_browser=True)


def test_null_window_manager_noop():
    """Verify NullWindowManager performs clean no-ops."""
    nwm = NullWindowManager()
    assert nwm.get_secondary_monitor_bounds() is None
    assert nwm.bring_browser_to_front("firefox") is False
    assert nwm.bring_to_front("edge") is False


def test_win32_window_manager_with_mock_user32(monkeypatch):
    """Verify Win32WindowManager monitor bounds and window management with injected user32."""
    monkeypatch.setattr("os.name", "nt")

    mock_user32 = MagicMock()

    # Simulate EnumDisplayMonitors
    def fake_enum_monitors(hdc, lprcClip, lpfnEnum, dwData):
        def fake_get_mon_info(hmon, p_mi):
            mi = getattr(p_mi, "_obj", None)
            if mi is not None:
                # hmon == 1 is primary (dwFlags = 1)
                # hmon == 2 is secondary (dwFlags = 0)
                is_primary = 1 if hmon == 1 else 0
                mi.dwFlags = is_primary
                mi.rcWork[0] = 0 if is_primary else 1920
                mi.rcWork[1] = 0
                mi.rcWork[2] = 1920 if is_primary else 3840
                mi.rcWork[3] = 1080
            return 1

        mock_user32.GetMonitorInfoW.side_effect = fake_get_mon_info

        # Trigger callback with primary (1) then secondary (2)
        lpfnEnum(1, 0, None, 0)
        lpfnEnum(2, 0, None, 0)
        return 1

    mock_user32.EnumDisplayMonitors.side_effect = fake_enum_monitors

    wm = Win32WindowManager(user32=mock_user32)
    bounds = wm.get_secondary_monitor_bounds()
    assert bounds == (1920, 0, 1920, 1080)


def test_win32_window_manager_window_positioning(monkeypatch):
    """Verify bring_browser_to_front locates window, restores, and sets position."""
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

    def fake_enum_windows(lpfnEnum, lparam):
        lpfnEnum(12345, 0)
        return 1

    mock_user32.EnumWindows.side_effect = fake_enum_windows

    wm = Win32WindowManager(user32=mock_user32)
    # Secondary monitor returns None
    monkeypatch.setattr(wm, "get_secondary_monitor_bounds", lambda: None)

    success = wm.bring_browser_to_front("firefox", "Tactical", focus_browser=True, max_retries=1, poll_interval=0.01)
    assert success is True
    # Asserts ShowWindow was called with SW_RESTORE (9) and SW_MAXIMIZE (3)
    mock_user32.ShowWindow.assert_any_call(12345, 9)
    mock_user32.ShowWindow.assert_any_call(12345, 3)
    mock_user32.BringWindowToTop.assert_called_with(12345)
    mock_user32.SetForegroundWindow.assert_called_with(12345)


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


def test_create_tactical_dashboard_direct(tmp_path):
    """Verify create_tactical_dashboard extracted into dashboard.py functions correctly."""
    memories = [
        {"topic": "tactics", "feature": "position", "title": "High Ground", "content": "Maintain sniper tower", "pinned": True}
    ]
    knowledge = [
        {"title": "Bala 5.56x45mm A1", "data_json": '{"tier": 4, "penetration": 42, "damage": 55}', "summary": "Armor piercing"}
    ]

    out_dir = tmp_path / "dashboard_test"
    result_path = dashboard_create(
        memory_items=memories,
        knowledge_items=knowledge,
        game="abi",
        output_dir=str(out_dir),
        auto_open=False,
    )

    assert result_path.exists()
    content = result_path.read_text(encoding="utf-8")
    assert "Dashboard Táctico - ABI" in content
    assert "High Ground" in content
    assert "Bala 5.56x45mm A1" in content
    assert "dashboardChart" in content


def test_window_manager_port_runtime_checkable():
    """Verify WindowManagerPort is decorated with @runtime_checkable and supports isinstance checks."""
    assert isinstance(NullWindowManager(), WindowManagerPort)
    assert isinstance(Win32WindowManager(), WindowManagerPort)

    class CustomWindowManager:
        def get_secondary_monitor_bounds(self):
            return None

        def bring_browser_to_front(self, browser_type: str, title_query: str = "", focus_browser: bool = False) -> bool:
            return True

    assert isinstance(CustomWindowManager(), WindowManagerPort)

    class NonWindowManager:
        pass

    assert not isinstance(NonWindowManager(), WindowManagerPort)


def test_win32_window_manager_safe_console_printing(monkeypatch, capsys):
    """Verify console messages in win32_window_manager do not contain emoji and encode safely under CP1252."""
    monkeypatch.setattr("os.name", "nt")

    mock_user32 = MagicMock()
    mock_user32.IsWindowVisible.return_value = 1
    mock_user32.IsIconic.return_value = 0

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

    success = wm.bring_browser_to_front("firefox", "Tactical", focus_browser=False, max_retries=1)
    assert success is True

    captured = capsys.readouterr()
    expected_msg = "[Mozilla Firefox] Reporte visual abierto y maximizado en DISPLAY2 (Secundaria)."
    assert expected_msg in captured.out
    # Must be encodable in standard Windows CP1252 without UnicodeEncodeError
    encoded = captured.out.encode("cp1252")
    assert "\U0001f310".encode("utf-8") not in encoded
    assert "🌐" not in captured.out


def test_tactical_report_template_repo_candidate_resolution(monkeypatch):
    """Verify repo_candidates[0] correctly resolves to template file when earlier tiers fail."""
    import abi_coach.infrastructure.resources.templates as tmpl

    candidate_0 = (
        Path(tmpl.__file__).resolve().parents[5]
        / "src"
        / "abi_coach"
        / "infrastructure"
        / "resources"
        / "templates"
        / "tactical_report.html"
    )
    assert candidate_0.is_file(), f"Candidate 0 path does not exist: {candidate_0}"

    import importlib.resources

    def raise_resource_error(*args, **kwargs):
        raise FileNotFoundError("Mock resource failure")

    monkeypatch.setattr(importlib.resources, "files", raise_resource_error)

    # Mock Path.is_file so that local_path is simulated as missing on first check
    orig_is_file = Path.is_file
    call_tracker = {"count": 0}

    def mock_is_file(self):
        if self.name == "tactical_report.html":
            call_tracker["count"] += 1
            if call_tracker["count"] == 1:
                return False  # Simulate local_path missing
        return orig_is_file(self)

    monkeypatch.setattr(Path, "is_file", mock_is_file)

    tmpl.load_tactical_report_template.cache_clear()
    loaded = tmpl.load_tactical_report_template()
    assert "{title}" in loaded
    assert call_tracker["count"] >= 2
    tmpl.load_tactical_report_template.cache_clear()

