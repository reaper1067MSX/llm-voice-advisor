"""HTML Report generation module for ABI Coach (Thin Facade).

Generates dark-themed, game-styled HTML reports with charts (Chart.js) and tables,
delegating platform operations to infrastructure adapters.
"""

import html
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Optional
import unicodedata

from abi_coach.application.slices.reporting.dashboard import create_tactical_dashboard
from abi_coach.infrastructure.adapters.platform.browser_launcher import (
    find_browser as _find_browser,
    open_and_maximize_in_browser,
)
from abi_coach.infrastructure.resources.templates import HTML_TEMPLATE

# Backward compatibility alias
open_and_maximize_in_chrome = open_and_maximize_in_browser


def _bring_browser_to_front_worker(
    browser_type: str, title_query: str = "", focus_browser: bool = False
) -> None:
    """Unminimize, move to secondary monitor, and maximize browser window (backward compatibility)."""
    if os.name != "nt":
        return
    from abi_coach.infrastructure.adapters.platform.win32_window_manager import (
        bring_browser_to_front_worker,
    )

    bring_browser_to_front_worker(browser_type, title_query, focus_browser)


def create_html_report(
    title: str,
    html_body: str,
    output_dir: str = "reports",
    auto_open: bool = True,
    opener: Optional[Callable[[str], Any]] = None,
    preferred_browser: str = "firefox",
    focus_browser: bool = False,
) -> Path:
    """Generate a styled HTML report and open it maximized in the preferred browser."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = int(time.time())
    ascii_title = unicodedata.normalize("NFKD", title).encode("ASCII", "ignore").decode("utf-8")
    safe_title = "".join(c if c.isalnum() else "_" for c in ascii_title).lower()[:30].strip("_")
    filename = f"report_{file_timestamp}_{safe_title}.html"
    file_path = out_path / filename

    safe_title_html = html.escape(title)

    full_html = HTML_TEMPLATE.format(
        title=safe_title_html,
        content=html_body,
        timestamp=timestamp_str,
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    if auto_open:
        resolved_str = str(file_path.resolve())
        if opener is not None:
            try:
                opener(resolved_str)
            except Exception:
                pass
        else:
            threading.Thread(
                target=open_and_maximize_in_browser,
                args=(resolved_str, title, preferred_browser, focus_browser),
                daemon=True,
            ).start()

    return file_path


__all__ = [
    "HTML_TEMPLATE",
    "create_html_report",
    "create_tactical_dashboard",
    "open_and_maximize_in_browser",
    "open_and_maximize_in_chrome",
    "_find_browser",
    "_bring_browser_to_front_worker",
]
