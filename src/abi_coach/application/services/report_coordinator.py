"""Tactical report coordinator managing HTML dashboard dispatch and tool invocation."""

from __future__ import annotations

from typing import Any, Callable, Optional

from abi_coach.application.slices.reporting.reports import create_html_report


class TacticalReportToolCoordinator:
    """Coordinates tactical HTML reports and tool callbacks decoupled from LLM providers."""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        auto_open: bool = True,
        opener: Optional[Callable[[str], Any]] = None,
        preferred_browser: Optional[str] = None,
        focus_browser: bool = False,
    ) -> None:
        self.output_dir = output_dir
        self.auto_open = auto_open
        self.opener = opener
        self.preferred_browser = preferred_browser
        self.focus_browser = focus_browser
        self.last_report_path: Optional[str] = None

    def create_report(self, title: str, html_body: str) -> str:
        """Generate and display HTML report, updating the last report path."""
        path = create_html_report(
            title=title,
            html_body=html_body,
            output_dir=self.output_dir,
            auto_open=self.auto_open,
            opener=self.opener,
            preferred_browser=self.preferred_browser,
            focus_browser=self.focus_browser,
        )
        self.last_report_path = str(path)
        return f"Informe HTML creado exitosamente en {path} y mostrado en pantalla."

    def create_tool_callback(self) -> Callable[[str, str], str]:
        """Return a callable compatible with LLM provider tool callbacks."""
        def _callback(title: str, html_body: str) -> str:
            return self.create_report(title, html_body)

        return _callback

    def render_context_dashboard(
        self,
        context_id: str,
        display_name: str,
        archetype_title: str,
    ) -> Optional[str]:
        """Render and open a standard gaming context activation dashboard."""
        html_body = f"""
        <div class="card">
            <h2>🎮 Contexto Activo: {display_name}</h2>
            <div class="badge-row" style="margin-top: 10px; margin-bottom: 15px;">
                <span class="badge badge-purple">Arquetipo: {archetype_title}</span>
                <span class="badge badge-blue">Contexto: {context_id}</span>
                <span class="badge badge-green">Estado: Conectado</span>
            </div>
            <p style="color: #9ca3af; line-height: 1.6;">
                El motor ha sincronizado las reglas tácticas de <strong>{display_name}</strong>, activado la memoria dinámica de arquetipo y purgado la caché L1 en RAM.
            </p>
        </div>
        """
        try:
            path = create_html_report(
                title=f"Dashboard: {display_name}",
                html_body=html_body,
                output_dir=self.output_dir,
                auto_open=self.auto_open,
                opener=self.opener,
                preferred_browser=self.preferred_browser,
                focus_browser=self.focus_browser,
            )
            self.last_report_path = str(path)
            return str(path)
        except Exception:
            self.last_report_path = None
            return None
