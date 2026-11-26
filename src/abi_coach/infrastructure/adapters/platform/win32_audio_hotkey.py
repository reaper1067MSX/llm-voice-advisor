"""Windows audio feedback beep and global mute hotkey monitor."""

import os
import threading
import time
from collections.abc import Callable
from typing import Any

VK_MAP: dict[str, int] = {
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}


def play_beep(freq: int, duration_ms: int) -> None:
    """Play a non-blocking Windows system beep for instant auditory feedback."""
    if os.name != "nt":
        return

    try:
        import winsound

        thread = threading.Thread(
            target=winsound.Beep,
            args=(freq, duration_ms),
            daemon=True,
        )
        thread.start()
    except (ImportError, OSError, RuntimeError):
        pass


class GlobalMuteHotkeyMonitor:
    """Background daemon polling thread for Windows global mute hotkey."""

    def __init__(
        self,
        mute_key: str = "f10",
        poll_interval_sec: float = 0.04,
    ) -> None:
        key_normalized = mute_key.lower().strip()
        self.mute_key = key_normalized
        self.vk_code = VK_MAP.get(key_normalized, 0x79)
        self.poll_interval_sec = poll_interval_sec

    def start(
        self,
        is_running: Callable[[], bool],
        on_toggle: Callable[[], Any],
    ) -> threading.Thread | None:
        """Start background daemon thread monitoring the global mute hotkey on Windows."""
        if os.name != "nt":
            return None

        import ctypes

        user32 = ctypes.windll.user32

        def _worker() -> None:
            was_down = False
            while is_running():
                try:
                    is_down = (user32.GetAsyncKeyState(self.vk_code) & 0x8000) != 0
                    if is_down and not was_down:
                        was_down = True
                        on_toggle()
                    elif not is_down and was_down:
                        was_down = False
                except (OSError, RuntimeError, ValueError):
                    pass
                time.sleep(self.poll_interval_sec)

        thread = threading.Thread(
            target=_worker,
            name="mute_hotkey_listener",
            daemon=True,
        )
        thread.start()
        return thread
