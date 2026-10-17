"""Tactical report coordinator acting as event host and listener for tool use."""

from __future__ import annotations

from typing import Any, Callable, Optional

from abi_coach.application.services.report_presenter import ReportPresenterService


class TacticalReportToolCoordinator:
    """Event host and dispatcher capturing tactical tool reporting events."""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        auto_open: bool = True,
        opener: Optional[Callable[[str], Any]] = None,
        preferred_browser: Optional[str] = None,
        focus_browser: bool = False,
        presenter: Optional[ReportPresenterService] = None,
    ) -> None:
        self.presenter = presenter or ReportPresenterService(
            output_dir=output_dir,
            auto_open=auto_open,
            opener=opener,
            preferred_browser=preferred_browser,
            focus_browser=focus_browser,
        )
        self.last_report_path: Optional[str] = None

    def create_report(self, title: str, html_body: str) -> str:
        """Handle report creation event and cache last report path."""
        path_str = self.presenter.render_report(title, html_body)
        self.last_report_path = path_str
        return f"Informe HTML creado exitosamente en {path_str} y mostrado en pantalla."

    def create_tool_callback(self) -> Callable[[str, str], str]:
        """Return a callable compatible with LLM provider tool callbacks."""
        return lambda title, html_body: self.create_report(title, html_body)

    def render_context_dashboard(
        self,
        context_id: str,
        display_name: str,
        archetype_title: str,
    ) -> Optional[str]:
        """Delegate context dashboard rendering and record path."""
        path_str = self.presenter.render_context_dashboard(context_id, display_name, archetype_title)
        self.last_report_path = path_str
        return path_str
