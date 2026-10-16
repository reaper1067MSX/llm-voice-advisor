"""Browser Display Adapter implementing ReportDisplayPort (Infrastructure Reporting)."""

from pathlib import Path
from typing import Any, Callable, Optional

from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result, fail, ok
from abi_coach.domain.ports.vision_port import ReportDisplayPort
from abi_coach.infrastructure.config.yaml_loader import ReportConfig
from abi_coach.application.slices.reporting.builder import TacticalReportBuilder
from abi_coach.application.slices.reporting.reports import create_html_report


class BrowserDisplayAdapter(ReportDisplayPort):
    """Hexagonal Adapter rendering HTML dashboards and positioning on DISPLAY2."""

    def __init__(
        self,
        config: ReportConfig,
        opener: Optional[Callable[[str], Any]] = None,
    ):
        self.config = config
        self.opener = opener

    def display_report(
        self,
        title: str,
        html_body: str,
        auto_open: bool = True,
    ) -> Result[Path, DomainError]:
        try:
            path = create_html_report(
                title=title,
                html_body=html_body,
                output_dir=self.config.output_dir,
                auto_open=auto_open and self.config.auto_open_browser,
                opener=self.opener,
                preferred_browser=self.config.preferred_browser,
                focus_browser=getattr(self.config, "focus_browser", False),
            )
            return ok(path)
        except Exception as e:
            return fail(
                DomainError(
                    code="REPORT_GENERATION_ERROR",
                    message=f"Fallo al abrir informe HTML en pantalla secundaria: {e}",
                    spoken_fallback="No pude abrir el panel gráfico en tu segundo monitor.",
                )
            )


__all__ = ["BrowserDisplayAdapter", "TacticalReportBuilder"]
