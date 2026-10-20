"""Window and display monitor management outbound port (Domain Layer)."""

from typing import Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class WindowManagerPort(Protocol):
    """Port for platform window positioning, monitor enumeration, and focus control."""

    def get_secondary_monitor_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Return the working area bounds (x, y, width, height) of the secondary monitor if present.

        Returns:
            Tuple of (x, y, width, height) in pixels, or None if no secondary monitor
            is detected or platform does not support multi-monitor enumeration.
        """
        ...

    def bring_browser_to_front(
        self,
        browser_type: str,
        title_query: str = "",
        focus_browser: bool = False,
    ) -> bool:
        """Locate target browser window, position on secondary monitor, and maximize.

        Args:
            browser_type: Browser identifier ('firefox', 'edge', 'chrome', or 'default').
            title_query: Substring filter to match against window title.
            focus_browser: If True, brings window to top and transfers foreground focus.
                          If False, ensures window is visible without stealing game focus.

        Returns:
            True if a matching window was found and positioned, False otherwise.
        """
        ...
