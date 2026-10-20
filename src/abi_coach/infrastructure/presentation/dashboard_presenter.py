"""Tactical dashboard presenter for HTML fragment generation and template formatting."""

from __future__ import annotations

import html
import json
import time
from typing import Any, List, Optional, Sequence, Union

from abi_coach.domain.entities.dashboard_records import (
    KnowledgeDashboardItem,
    MemoryDashboardItem,
)
from abi_coach.infrastructure.resources.templates import HTML_TEMPLATE


class DashboardPresenter:
    """Presenter responsible for HTML rendering of the tactical dashboard."""

    @staticmethod
    def render_memory_card(item: MemoryDashboardItem) -> str:
        """Render a single memory card HTML element."""
        if not isinstance(item, MemoryDashboardItem):
            item = MemoryDashboardItem.from_raw(item)
        pin = "⭐ " if item.pinned else ""
        escaped_title = html.escape(item.title)
        escaped_content = html.escape(item.content)
        escaped_topic = html.escape(item.topic)
        escaped_feature = html.escape(item.feature)
        return (
            f"<div class='card' style='margin-bottom:12px;'>"
            f"<h3>{pin}{escaped_title}</h3>"
            f"<p style='color:var(--text-secondary);font-size:0.85rem;'>[{escaped_topic}/{escaped_feature}]</p>"
            f"<p style='margin-top:6px;'>{escaped_content}</p>"
            f"</div>"
        )

    @classmethod
    def render_memory_column(cls, items: Sequence[MemoryDashboardItem]) -> str:
        """Render the complete memory column or empty placeholder."""
        if not items:
            return "<p style='color:var(--text-secondary);'>Sin memorias guardadas aún.</p>"
        return "".join(cls.render_memory_card(item) for item in items)

    @staticmethod
    def get_tier_badge_color(tier: Any) -> str:
        """Resolve CSS variable for tactical tier badges."""
        t_str = str(tier)
        colors = {
            "3": "var(--tier3)",
            "4": "var(--tier4)",
            "5": "var(--tier5)",
            "6": "var(--tier6)",
        }
        return colors.get(t_str, "var(--text-secondary)")

    @classmethod
    def render_knowledge_row(cls, item: KnowledgeDashboardItem) -> str:
        """Render a single table row for a tactical knowledge item."""
        if not isinstance(item, KnowledgeDashboardItem):
            item = KnowledgeDashboardItem.from_raw(item)
        escaped_title = html.escape(item.title)
        escaped_summary = html.escape(item.summary)
        escaped_tier = html.escape(str(item.tier))
        escaped_pen = html.escape(str(item.penetration))
        escaped_dmg = html.escape(str(item.damage))
        badge_color = cls.get_tier_badge_color(item.tier)
        return (
            f"<tr>"
            f"<td><strong>{escaped_title}</strong></td>"
            f"<td><span style='color:{badge_color};font-weight:bold;'>Tier {escaped_tier}</span></td>"
            f"<td>{escaped_pen}</td>"
            f"<td>{escaped_dmg}</td>"
            f"<td style='font-size:0.85rem;color:var(--text-secondary);'>{escaped_summary}</td>"
            f"</tr>"
        )

    @classmethod
    def render_knowledge_table(cls, items: Sequence[KnowledgeDashboardItem]) -> str:
        """Render knowledge items inside a styled HTML table."""
        rows = "".join(cls.render_knowledge_row(item) for item in items)
        return f"""
        <table style="width:100%;border-collapse:collapse;text-align:left;">
            <thead>
                <tr style="border-bottom:2px solid var(--border);color:var(--accent);">
                    <th style="padding:8px;">Objeto</th>
                    <th style="padding:8px;">Tier</th>
                    <th style="padding:8px;">Pen.</th>
                    <th style="padding:8px;">Daño</th>
                    <th style="padding:8px;">Resumen</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """

    @classmethod
    def render_ballistics_chart(cls, items: Sequence[KnowledgeDashboardItem]) -> str:
        """Render the Chart.js comparative canvas and script block if ballistic data exists."""
        labels: List[str] = []
        pen_data: List[Union[int, float]] = []
        dmg_data: List[Union[int, float]] = []

        for item in items:
            typed_item = (
                item if isinstance(item, KnowledgeDashboardItem) else KnowledgeDashboardItem.from_raw(item)
            )
            if typed_item.has_ballistic_data:
                labels.append(typed_item.short_name)
                pen_data.append(typed_item.penetration)  # type: ignore[arg-type]
                dmg_data.append(typed_item.damage)  # type: ignore[arg-type]

        if not labels:
            return ""

        return f"""
        <div class="card" style="margin-top:20px;">
            <h2>Comparativa Balística en Tiempo Real</h2>
            <div class="chart-container" style="position:relative;height:240px;width:100%;">
                <canvas id="dashboardChart"></canvas>
            </div>
        </div>
        <script>
            new Chart(document.getElementById('dashboardChart'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [
                        {{ label: 'Penetración', data: {json.dumps(pen_data)}, backgroundColor: '#f59e0b' }},
                        {{ label: 'Daño Base', data: {json.dumps(dmg_data)}, backgroundColor: '#3b82f6' }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ labels: {{ color: '#f3f4f6' }} }} }},
                    scales: {{
                        x: {{ ticks: {{ color: '#9ca3af' }}, grid: {{ color: '#2e3542' }} }},
                        y: {{ ticks: {{ color: '#9ca3af' }}, grid: {{ color: '#2e3542' }} }}
                    }}
                }}
            }});
        </script>
        """

    @classmethod
    def render_dashboard_body(
        cls,
        memory_items: Sequence[Union[MemoryDashboardItem, Any]],
        knowledge_items: Sequence[Union[KnowledgeDashboardItem, Any]],
    ) -> str:
        """Compose the responsive 2-column tactical dashboard body."""
        typed_memories = [
            m if isinstance(m, MemoryDashboardItem) else MemoryDashboardItem.from_raw(m)
            for m in (memory_items or [])
        ]
        typed_knowledge = [
            k if isinstance(k, KnowledgeDashboardItem) else KnowledgeDashboardItem.from_raw(k)
            for k in (knowledge_items or [])
        ]

        mem_cards_html = cls.render_memory_column(typed_memories)
        table_html = cls.render_knowledge_table(typed_knowledge)
        chart_html = cls.render_ballistics_chart(typed_knowledge)

        return f"""
        <div style="display:grid;grid-template-columns: 1fr 2fr; gap:24px;">
            <div>
                <h2>🧠 Perfil & Memoria Persistente</h2>
                <div style="margin-top:14px;">
                    {mem_cards_html}
                </div>
            </div>
            <div>
                <h2>🎯 Base de Conocimiento Táctico (RAG Local)</h2>
                <div class="card" style="margin-top:14px;overflow-x:auto;">
                    {table_html}
                </div>
                {chart_html}
            </div>
        </div>
        """

    @classmethod
    def render_page(
        cls,
        memory_items: Sequence[Union[MemoryDashboardItem, Any]],
        knowledge_items: Sequence[Union[KnowledgeDashboardItem, Any]],
        game: str = "abi",
        timestamp: Optional[str] = None,
    ) -> str:
        """Render complete HTML document populated into HTML_TEMPLATE."""
        body = cls.render_dashboard_body(memory_items, knowledge_items)
        ts = timestamp or time.strftime("%Y-%m-%d %H:%M:%S")
        return HTML_TEMPLATE.format(
            title=f"Dashboard Táctico - {game.upper()}",
            content=body,
            timestamp=ts,
        )


__all__ = [
    "DashboardPresenter",
]
