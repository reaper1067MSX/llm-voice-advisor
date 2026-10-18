"""Tactical Dashboard generation combining player memory and game knowledge."""

import html
import json
from pathlib import Path
import threading
import time
from typing import Any, Callable, Optional

from abi_coach.infrastructure.adapters.platform.browser_launcher import (
    open_and_maximize_in_browser,
)
from abi_coach.infrastructure.resources.templates import HTML_TEMPLATE


def create_tactical_dashboard(
    memory_items: list,
    knowledge_items: list,
    game: str = "abi",
    output_dir: str = "reports",
    auto_open: bool = False,
    opener: Optional[Callable[[str], Any]] = None,
    preferred_browser: str = "firefox",
    focus_browser: bool = False,
) -> Path:
    """Generate a consolidated tactical live dashboard combining player memory and game knowledge."""
    # 1. Build Memory Column
    mem_cards = []
    if memory_items:
        for m in memory_items:
            pin = "⭐ " if m.get("pinned") else ""
            mem_cards.append(
                f"<div class='card' style='margin-bottom:12px;'>"
                f"<h3>{pin}{html.escape(m.get('title', ''))}</h3>"
                f"<p style='color:var(--text-secondary);font-size:0.85rem;'>[{m.get('topic')}/{m.get('feature')}]</p>"
                f"<p style='margin-top:6px;'>{html.escape(m.get('content', ''))}</p>"
                f"</div>"
            )
    else:
        mem_cards.append("<p style='color:var(--text-secondary);'>Sin memorias guardadas aún.</p>")

    # 2. Build Knowledge Table & Chart Data
    table_rows = []
    labels = []
    pen_data = []
    dmg_data = []

    for k in knowledge_items:
        tit = html.escape(k.get("title", ""))
        data = {}
        try:
            data = json.loads(k.get("data_json", "{}"))
        except Exception:
            pass

        tier = data.get("tier", "-")
        pen = data.get("penetration", "-")
        dmg = data.get("damage", "-")

        badge_color = "var(--text-secondary)"
        if str(tier) == "3":
            badge_color = "var(--tier3)"
        elif str(tier) == "4":
            badge_color = "var(--tier4)"
        elif str(tier) == "5":
            badge_color = "var(--tier5)"
        elif str(tier) == "6":
            badge_color = "var(--tier6)"

        table_rows.append(
            f"<tr>"
            f"<td><strong>{tit}</strong></td>"
            f"<td><span style='color:{badge_color};font-weight:bold;'>Tier {tier}</span></td>"
            f"<td>{pen}</td>"
            f"<td>{dmg}</td>"
            f"<td style='font-size:0.85rem;color:var(--text-secondary);'>{html.escape(k.get('summary', ''))}</td>"
            f"</tr>"
        )

        if isinstance(pen, (int, float)) and isinstance(dmg, (int, float)):
            short_name = tit.replace("Bala 7.62x51mm ", "").replace("Bala 9x19mm ", "").replace("Bala 5.56x45mm ", "")
            labels.append(short_name)
            pen_data.append(pen)
            dmg_data.append(dmg)

    chart_html = ""
    if labels:
        chart_html = f"""
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

    dashboard_body = f"""
    <div style="display:grid;grid-template-columns: 1fr 2fr; gap:24px;">
        <div>
            <h2>🧠 Perfil & Memoria Persistente</h2>
            <div style="margin-top:14px;">
                {''.join(mem_cards)}
            </div>
        </div>
        <div>
            <h2>🎯 Base de Conocimiento Táctico (RAG Local)</h2>
            <div class="card" style="margin-top:14px;overflow-x:auto;">
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
                        {''.join(table_rows)}
                    </tbody>
                </table>
            </div>
            {chart_html}
        </div>
    </div>
    """

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    dashboard_file = out_path / "dashboard.html"

    full_html = HTML_TEMPLATE.format(
        title=f"Dashboard Táctico - {game.upper()}",
        content=dashboard_body,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
    )

    with open(dashboard_file, "w", encoding="utf-8") as f:
        f.write(full_html)

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


__all__ = ["create_tactical_dashboard"]
