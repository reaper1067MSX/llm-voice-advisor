"""Platform adapters package (Win32 window management, browser launching, audio hotkeys)."""

from abi_coach.infrastructure.adapters.platform.browser_launcher import (
    BrowserLauncher,
    find_browser,
    open_and_maximize_in_browser,
    open_and_maximize_in_chrome,
    open_in_browser,
)
from abi_coach.infrastructure.adapters.platform.win32_audio_hotkey import (
    VK_MAP,
    GlobalMuteHotkeyMonitor,
    play_beep,
)
from abi_coach.infrastructure.adapters.platform.win32_window_manager import (
    NullWindowManager,
    Win32WindowManager,
    bring_browser_to_front_worker,
    get_default_window_manager,
)

__all__ = [
    "BrowserLauncher",
    "find_browser",
    "open_and_maximize_in_browser",
    "open_and_maximize_in_chrome",
    "open_in_browser",
    "Win32WindowManager",
    "NullWindowManager",
    "bring_browser_to_front_worker",
    "get_default_window_manager",
    "VK_MAP",
    "play_beep",
    "GlobalMuteHotkeyMonitor",
]
