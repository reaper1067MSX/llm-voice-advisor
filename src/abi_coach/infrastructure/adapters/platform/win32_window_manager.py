"""Win32 Platform Window Manager Adapter implementing WindowManagerPort.

Provides secondary monitor discovery, window enumeration, unminimizing,
positioning, and maximizing via user32 ctypes on Windows, with graceful
no-op degradation on non-Windows platforms or when user32 fails.
"""

import os
import time
from typing import Any, List, Optional, Tuple

from abi_coach.domain.ports.window_manager_port import WindowManagerPort


class Win32WindowManager(WindowManagerPort):
    """Adapter for Windows window positioning and multi-monitor management via user32 ctypes."""

    # Win32 ShowWindow commands
    SW_MAXIMIZE = 3
    SW_RESTORE = 9

    # Win32 SetWindowPos flags
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040

    # Win32 Monitor flags
    MONITORINFOF_PRIMARY = 0x00000001

    # Heuristic signatures for supported browsers
    FIREFOX_WINDOW_CLASS = "MozillaWindowClass"
    CHROME_EDGE_WINDOW_CLASS = "Chrome_WidgetWin_1"
    EXCLUDED_ELECTRON_APPS = (
        "visual studio code",
        "discord",
        "slack",
        "spotify",
        "teams",
    )

    def __init__(self, user32: Any = None):
        """Initialize adapter with optional injected user32 DLL for testing."""
        self._injected_user32 = user32

    def _get_user32(self) -> Any:
        """Resolve user32 DLL safely, returning None on non-Windows or failure."""
        if self._injected_user32 is not None:
            return self._injected_user32
        if os.name != "nt":
            return None
        try:
            import ctypes

            return getattr(ctypes.windll, "user32", None)
        except Exception:
            return None

    def get_secondary_monitor_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get the working area bounds (x, y, w, h) of the secondary monitor if present."""
        if os.name != "nt":
            return None

        user32 = self._get_user32()
        if not user32:
            return None

        try:
            import ctypes

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", ctypes.c_long * 4),
                    ("rcWork", ctypes.c_long * 4),
                    ("dwFlags", ctypes.c_ulong),
                ]

            secondary_bounds: Optional[Tuple[int, int, int, int]] = None

            def monitor_cb(hmon, hdc, lprect, lparam):
                nonlocal secondary_bounds
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                    is_primary = bool(mi.dwFlags & self.MONITORINFOF_PRIMARY)
                    if not is_primary:
                        x = mi.rcWork[0]
                        y = mi.rcWork[1]
                        w = mi.rcWork[2] - mi.rcWork[0]
                        h = mi.rcWork[3] - mi.rcWork[1]
                        secondary_bounds = (x, y, w, h)
                return True

            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_long * 4),
                ctypes.c_void_p,
            )
            user32.EnumDisplayMonitors(0, 0, MONITORENUMPROC(monitor_cb), 0)
            return secondary_bounds
        except Exception:
            return None

    def bring_browser_to_front(
        self,
        browser_type: str,
        title_query: str = "",
        focus_browser: bool = False,
        max_retries: int = 15,
        poll_interval: float = 0.2,
    ) -> bool:
        """Unminimize, move to secondary monitor, and maximize browser window without invasive hooks."""
        if os.name != "nt":
            return False

        user32 = self._get_user32()
        if not user32:
            return False

        try:
            import ctypes
            from ctypes import wintypes

            sec_bounds = self.get_secondary_monitor_bounds()
            target_hwnd = None
            lower_query = title_query.lower().strip() if title_query else ""

            # Poll for window creation (up to max_retries * poll_interval seconds)
            for _ in range(max_retries):
                time.sleep(poll_interval)
                matching_hwnds: List[Any] = []

                def enum_cb(hwnd, lparam):
                    if not user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
                        return True

                    cls_buf = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, cls_buf, 256)
                    cls_val = cls_buf.value

                    title_buf = ctypes.create_unicode_buffer(512)
                    user32.GetWindowTextW(hwnd, title_buf, 512)
                    w_title = title_buf.value.lower()

                    if browser_type == "firefox":
                        if cls_val == self.FIREFOX_WINDOW_CLASS or (
                            "firefox" in w_title or (lower_query and lower_query in w_title)
                        ):
                            matching_hwnds.append(hwnd)
                    elif browser_type in ("edge", "chrome"):
                        if cls_val == self.CHROME_EDGE_WINDOW_CLASS:
                            # Exclude non-browser Electron apps
                            if not any(app in w_title for app in self.EXCLUDED_ELECTRON_APPS):
                                expected = "edge" if browser_type == "edge" else "chrome"
                                if expected in w_title or (lower_query and lower_query in w_title):
                                    matching_hwnds.append(hwnd)
                    return True

                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
                user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

                if matching_hwnds:
                    target_hwnd = matching_hwnds[0]
                    break

            if not target_hwnd:
                return False

            # 1. Un-minimize if iconic
            if user32.IsIconic(target_hwnd):
                user32.ShowWindow(target_hwnd, self.SW_RESTORE)

            # 2. Position on secondary monitor if detected
            if sec_bounds:
                sx, sy, sw, sh = sec_bounds
                user32.ShowWindow(target_hwnd, self.SW_RESTORE)
                user32.SetWindowPos(target_hwnd, 0, sx, sy, sw - 10, sh - 10, self.SWP_SHOWWINDOW)

            # 3. Ensure maximized
            user32.ShowWindow(target_hwnd, self.SW_MAXIMIZE)

            if focus_browser:
                user32.BringWindowToTop(target_hwnd)
                user32.SetForegroundWindow(target_hwnd)
            else:
                user32.SetWindowPos(
                    target_hwnd,
                    0,
                    0,
                    0,
                    0,
                    0,
                    self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW | self.SWP_NOACTIVATE,
                )

            mon_label = "DISPLAY2 (Secundaria)" if sec_bounds else "Pantalla principal"
            browser_names = {
                "firefox": "Mozilla Firefox",
                "edge": "Microsoft Edge",
                "chrome": "Google Chrome",
            }
            b_label = browser_names.get(browser_type, browser_type.title())
            print(f"[{b_label}] Reporte visual abierto y maximizado en {mon_label}.", flush=True)
            return True

        except Exception:
            return False

    bring_to_front = bring_browser_to_front


class NullWindowManager(WindowManagerPort):
    """No-op window manager for non-Windows platforms or headless test execution."""

    def get_secondary_monitor_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        return None

    def bring_browser_to_front(
        self,
        browser_type: str,
        title_query: str = "",
        focus_browser: bool = False,
    ) -> bool:
        return False

    bring_to_front = bring_browser_to_front


def bring_browser_to_front_worker(
    browser_type: str, title_query: str = "", focus_browser: bool = False
) -> None:
    """Standalone worker function for positioning browser window."""
    if os.name != "nt":
        return
    wm = Win32WindowManager()
    wm.bring_browser_to_front(browser_type, title_query=title_query, focus_browser=focus_browser)


_bring_browser_to_front_worker = bring_browser_to_front_worker


def get_default_window_manager() -> WindowManagerPort:
    """Return platform-appropriate window manager instance."""
    if os.name == "nt":
        return Win32WindowManager()
    return NullWindowManager()


__all__ = [
    "Win32WindowManager",
    "NullWindowManager",
    "bring_browser_to_front_worker",
    "_bring_browser_to_front_worker",
    "get_default_window_manager",
]
