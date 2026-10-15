"""Backward compatibility shim for abi_coach.reports -> abi_coach.slices.reporting."""

from abi_coach.slices.reporting.builder import TacticalReportBuilder
from abi_coach.slices.reporting.reports import (
    HTML_TEMPLATE,
    _bring_browser_to_front_worker,
    _find_browser,
    _get_process_name_for_hwnd,
    _get_secondary_monitor_bounds,
    create_html_report,
    create_tactical_dashboard,
    open_and_maximize_in_browser,
)

__all__ = [
    "HTML_TEMPLATE",
    "_find_browser",
    "_get_secondary_monitor_bounds",
    "_get_process_name_for_hwnd",
    "_bring_browser_to_front_worker",
    "open_and_maximize_in_browser",
    "create_html_report",
    "create_tactical_dashboard",
    "TacticalReportBuilder",
]
