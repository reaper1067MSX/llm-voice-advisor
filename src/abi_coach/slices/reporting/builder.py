"""Tactical report builder implementing the Builder Pattern for rich game dashboards."""

import html
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional

from abi_coach.slices.reporting.reports import create_html_report


class TacticalReportBuilder:
    """Fluent Builder for generating structured, styled tactical HTML dashboards and charts."""

    def __init__(self, title: str = "Informe Táctico", game_badge: str = "Tactical Copilot"):
        self.title = title
        self.game_badge = game_badge
        self._sections: List[str] = []
        self._badges: List[str] = []
        self._charts_js: List[str] = []

    def add_badge(self, label: str, value: str, color: str = "amber") -> "TacticalReportBuilder":
        """Add a summary badge pill to the header section."""
        # Colors: amber, purple, green, blue, pink
        color_class = f"badge-{color}" if color != "amber" else "badge"
        self._badges.append(
            f'<span class="{color_class}"><strong>{html.escape(label)}:</strong> {html.escape(str(value))}</span>'
        )
        return self

    def add_card(self, title: str, content_html: str) -> "TacticalReportBuilder":
        """Add a dark-themed card section with a title and arbitrary HTML body."""
        card_html = f"""
        <div class="card">
            <h2>{html.escape(title)}</h2>
            <div>{content_html}</div>
        </div>
        """
        self._sections.append(card_html)
        return self

    def add_table(self, headers: List[str], rows: List[List[Any]], title: Optional[str] = None) -> "TacticalReportBuilder":
        """Add a styled data table with headers and row values."""
        th_elements = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
        tr_elements = []
        for row in rows:
            tds = "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row)
            tr_elements.append(f"<tr>{tds}</tr>")
        rows_html = "".join(tr_elements)

        table_content = f"""
        <table>
            <thead>
                <tr>{th_elements}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """
        if title:
            return self.add_card(title, table_content)
        self._sections.append(table_content)
        return self

    def add_chart(
        self,
        chart_id: str,
        chart_type: str,
        labels: List[str],
        datasets: List[Dict[str, Any]],
        title: Optional[str] = None,
    ) -> "TacticalReportBuilder":
        """Add an interactive Chart.js chart embedded in a responsive card."""
        clean_id = "".join(c if c.isalnum() else "_" for c in chart_id)
        canvas_html = f"""
        <div class="chart-container">
            <canvas id="{clean_id}"></canvas>
        </div>
        """
        config_json = json.dumps(
            {
                "type": chart_type,
                "data": {
                    "labels": labels,
                    "datasets": datasets,
                },
                "options": {
                    "responsive": True,
                    "maintainAspectRatio": False,
                    "plugins": {
                        "legend": {"labels": {"color": "#9ca3af"}},
                    },
                    "scales": {
                        "x": {"ticks": {"color": "#9ca3af"}, "grid": {"color": "#2e3542"}},
                        "y": {"ticks": {"color": "#9ca3af"}, "grid": {"color": "#2e3542"}},
                    },
                },
            }
        )

        script_html = f"""
        <script>
            (function() {{
                const ctx = document.getElementById('{clean_id}').getContext('2d');
                new Chart(ctx, {config_json});
            }})();
        </script>
        """

        combined = canvas_html + script_html
        if title:
            return self.add_card(title, combined)
        self._sections.append(combined)
        return self

    def build_body(self) -> str:
        """Return the combined inner HTML body."""
        parts = []
        if self._badges:
            badge_row = f'<div class="badge-row" style="margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap;">{"".join(self._badges)}</div>'
            parts.append(badge_row)
        parts.extend(self._sections)
        return "\n".join(parts)

    def save_and_open(
        self,
        output_dir: str = "reports",
        auto_open: bool = True,
        opener: Optional[Callable[[str], Any]] = None,
        preferred_browser: str = "firefox",
        focus_browser: bool = False,
    ) -> Path:
        """Compile report and display on secondary monitor."""
        return create_html_report(
            title=self.title,
            html_body=self.build_body(),
            output_dir=output_dir,
            auto_open=auto_open,
            opener=opener,
            preferred_browser=preferred_browser,
            focus_browser=focus_browser,
        )
