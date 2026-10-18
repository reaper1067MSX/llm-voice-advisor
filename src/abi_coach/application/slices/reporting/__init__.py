"""Tactical reporting vertical slice: rich dark-themed dashboards, secondary monitor management, and chart generation."""

from abi_coach.application.slices.reporting.builder import TacticalReportBuilder
from abi_coach.application.slices.reporting.dashboard import (
    KnowledgeDashboardItem,
    MemoryDashboardItem,
)
from abi_coach.application.slices.reporting.reports import (
    create_html_report,
    create_tactical_dashboard,
    open_and_maximize_in_browser,
)

__all__ = [
    "TacticalReportBuilder",
    "create_html_report",
    "create_tactical_dashboard",
    "open_and_maximize_in_browser",
    "MemoryDashboardItem",
    "KnowledgeDashboardItem",
]
