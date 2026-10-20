"""Tactical Dashboard generation coordinating player memory and game knowledge."""

from __future__ import annotations

from pathlib import Path
import threading
from typing import Any, Callable, Optional, Sequence, Union

from abi_coach.domain.entities.dashboard_records import (
    KnowledgeDashboardItem,
    MemoryDashboardItem,
)
from abi_coach.infrastructure.adapters.platform.browser_launcher import (
    open_and_maximize_in_browser,
)
from abi_coach.infrastructure.presentation.dashboard_presenter import DashboardPresenter


def create_tactical_dashboard(
    memory_items: Sequence[Union[MemoryDashboardItem, dict, Any]],
    knowledge_items: Sequence[Union[KnowledgeDashboardItem, dict, Any]],
    game: str = "abi",
    output_dir: str = "reports",
    auto_open: bool = False,
    opener: Optional[Callable[[str], Any]] = None,
    preferred_browser: str = "firefox",
    focus_browser: bool = False,
) -> Path:
    """Generate a consolidated tactical live dashboard combining player memory and game knowledge."""
    # 1. Normalize items to strongly-typed domain DTOs
    typed_memories = [MemoryDashboardItem.from_raw(m) for m in (memory_items or [])]
    typed_knowledge = [KnowledgeDashboardItem.from_raw(k) for k in (knowledge_items or [])]

    # 2. Render HTML document via Presentation Infrastructure
    full_html = DashboardPresenter.render_page(
        memory_items=typed_memories,
        knowledge_items=typed_knowledge,
        game=game,
    )

    # 3. Output file writing
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    dashboard_file = out_path / "dashboard.html"

    with open(dashboard_file, "w", encoding="utf-8") as f:
        f.write(full_html)

    # 4. Browser launching
    if auto_open:
        resolved_str = str(dashboard_file.resolve())
        if opener is not None:
            try:
                opener(resolved_str)
            except Exception:
                pass
        else:
            threading.Thread(
                target=open_and_maximize_in_browser,
                args=(resolved_str, "Dashboard Táctico", preferred_browser, focus_browser),
                daemon=True,
            ).start()

    return dashboard_file


__all__ = [
    "create_tactical_dashboard",
    "MemoryDashboardItem",
    "KnowledgeDashboardItem",
]
