"""Browser Launcher adapter for ABI Coach (Platform Infrastructure).

Discovers browser executables (Firefox, Chrome, Edge) across standard Windows
paths and system PATH, launching them with new-window flags and fallback to webbrowser.
"""

import os
from pathlib import Path
import shutil
import subprocess
import threading
from typing import Any, Callable, List, Optional, Tuple
import webbrowser

from abi_coach.infrastructure.adapters.platform.win32_window_manager import (
    get_default_window_manager,
)


class BrowserLauncher:
    """Discovers and launches browser instances with resilient fallback."""

    def __init__(self, window_manager: Optional[Any] = None) -> None:
        self.window_manager = window_manager

    @staticmethod
    def _check_firefox() -> Optional[str]:
        ff_cmd = shutil.which("firefox") or shutil.which("firefox.exe")
        if ff_cmd and os.path.isfile(ff_cmd):
            return ff_cmd
        candidates = [
            os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps\firefox.exe"),
            os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    @staticmethod
    def _check_edge() -> Optional[str]:
        edge_cmd = shutil.which("msedge") or shutil.which("msedge.exe")
        if edge_cmd and os.path.isfile(edge_cmd):
            return edge_cmd
        candidates = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    @staticmethod
    def _check_chrome() -> Optional[str]:
        chrome_cmd = shutil.which("chrome") or shutil.which("chrome.exe")
        if chrome_cmd and os.path.isfile(chrome_cmd):
            return chrome_cmd
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    def find_browser(self, preferred: str = "firefox") -> Tuple[str, Optional[str]]:
        """Locate browser executable on Windows based on preference with smart fallback.

        Returns:
            Tuple of (browser_type, executable_path_or_none).
            If no browser is found, returns ("default", None).
        """
        pref = preferred.lower().strip()
        if pref == "edge":
            order = [
                ("edge", self._check_edge),
                ("firefox", self._check_firefox),
                ("chrome", self._check_chrome),
            ]
        elif pref == "chrome":
            order = [
                ("chrome", self._check_chrome),
                ("firefox", self._check_firefox),
                ("edge", self._check_edge),
            ]
        else:  # default "firefox"
            order = [
                ("firefox", self._check_firefox),
                ("edge", self._check_edge),
                ("chrome", self._check_chrome),
            ]

        for b_type, check_fn in order:
            path = check_fn()
            if path:
                return (b_type, path)

        return ("default", None)

    @staticmethod
    def get_browser_args(browser_type: str, browser_path: str, target: str) -> List[str]:
        """Format CLI flags: '-new-window' for Firefox, '--new-window' for Chromium."""
        flag = "-new-window" if browser_type == "firefox" else "--new-window"
        return [browser_path, flag, target]

    def launch_browser_process(
        self,
        browser_type: str,
        browser_path: str,
        file_path: str,
    ) -> subprocess.Popen:
        """Launch the browser process using subprocess.Popen with shell=False."""
        args = self.get_browser_args(browser_type, browser_path, file_path)
        startupinfo = subprocess.STARTUPINFO() if os.name == "nt" else None
        return subprocess.Popen(args, startupinfo=startupinfo, shell=False)

    def open(
        self,
        file_path: str,
        title: str = "",
        preferred: str = "firefox",
        focus_browser: bool = False,
    ) -> bool:
        """Open file_path in preferred browser, invoke window manager, or fall back to webbrowser.

        Returns:
            True if launched via subprocess, False if standard webbrowser fallback was used.
        """
        b_type, b_path = self.find_browser(preferred=preferred)

        if b_path:
            try:
                self.launch_browser_process(b_type, b_path, file_path)

                # Trigger window manager if available
                wm = self.window_manager or get_default_window_manager()
                trigger_fn = getattr(
                    wm,
                    "bring_browser_to_front",
                    getattr(wm, "bring_to_front", None),
                )
                if callable(trigger_fn):
                    threading.Thread(
                        target=trigger_fn,
                        args=(b_type, title, focus_browser),
                        daemon=True,
                    ).start()
                return True
            except Exception:
                pass

        # Resilient fallback
        try:
            webbrowser.open(file_path)
        except Exception:
            pass
        return False


_default_launcher = BrowserLauncher()


def find_browser(preferred: str = "firefox") -> Tuple[str, Optional[str]]:
    """Locate browser executable on Windows based on user preference."""
    return _default_launcher.find_browser(preferred=preferred)


_find_browser = find_browser


def open_and_maximize_in_browser(
    file_path: str,
    title: str = "",
    preferred: str = "firefox",
    focus_browser: bool = False,
    window_manager: Optional[Any] = None,
) -> None:
    """Open file in preferred browser, position and maximize on secondary monitor."""
    launcher = BrowserLauncher(window_manager=window_manager) if window_manager else _default_launcher
    launcher.open(file_path, title=title, preferred=preferred, focus_browser=focus_browser)


open_in_browser = open_and_maximize_in_browser
open_and_maximize_in_chrome = open_and_maximize_in_browser

__all__ = [
    "BrowserLauncher",
    "find_browser",
    "_find_browser",
    "open_and_maximize_in_browser",
    "open_and_maximize_in_chrome",
    "open_in_browser",
]
